# Architecture

## Design principles

1. **Clean Architecture / dependency inversion.** The RAG pipeline (`app/rag/`) and services (`app/services/`) depend only on abstract interfaces (`BaseLLMProvider`, `BaseEmbeddingProvider`, `BaseVectorStore`, `BaseReranker`, `BasePDFParser`, `BaseStorageProvider`). Concrete implementations live in provider-specific modules and are wired up by small `factory.py` files that read `Settings`. Nothing in the business logic imports `openai`, `faiss`, or any vendor SDK directly.
2. **Layered flow.** `API routes → Services → Repositories → SQLAlchemy models`, with cross-cutting concerns (auth, logging, rate limiting) as FastAPI dependencies/middleware rather than scattered through business logic.
3. **Provider-independence as a first-class requirement**, not an afterthought — every "pluggable" component in the spec (LLM, embeddings, vector store, PDF parser, storage, reranker) has a `base.py` interface and a `factory.py` that switches on a `Settings` field.
4. **Two data stores with distinct jobs.** PostgreSQL is the source of truth for text, metadata, users, and chat history. The vector store holds only embeddings + light metadata keyed by the same chunk UUID — this is what makes swapping FAISS↔Chroma safe: no business logic depends on which one is active.

## Component diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              React Frontend                              │
│   Login/Register · Upload · Library · Chat · History · Profile           │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │ REST (Axios + React Query, JWT bearer)
┌───────────────────────────────▼────────────────────────────────────────┐
│                             FastAPI (app/api)                            │
│  auth_routes · brochure_routes · chat_routes · health_routes             │
│  middleware: CORS, rate limiting, structured request logging             │
│  dependency: get_current_user (JWT) via app/dependencies/auth.py         │
└───────┬───────────────────────┬───────────────────────┬─────────────────┘
        │                       │                       │
┌───────▼────────┐   ┌──────────▼─────────┐   ┌─────────▼──────────┐
│  AuthService    │   │  BrochureService    │   │   ChatService       │
│  (register/     │   │  upload → parse →   │   │  session mgmt +     │
│   login)        │   │  chunk → embed →     │   │  RagPipeline.answer │
│                 │   │  index               │   │                     │
└───────┬─────────┘   └──────────┬──────────┘   └─────────┬───────────┘
        │                        │                          │
┌───────▼────────────────────────▼──────────────────────────▼───────────┐
│                    Repositories (app/repositories)                      │
│      UserRepository · BrochureRepository · ChunkRepository ·           │
│                          ChatRepository                                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                 │ SQLAlchemy 2.0 async
┌───────────────────────────────▼─────────────────────────────────────────┐
│                          PostgreSQL                                      │
│     users · brochures · chunks · chat_sessions · chat_messages          │
└────────────────────────────────────────────────────────────────────────┘

  Provider seams used by BrochureService / RagPipeline (all behind interfaces):

  BasePDFParser        →  PyMuPDFParser | PDFPlumberParser
  BaseEmbeddingProvider →  SentenceTransformerEmbeddingProvider | OpenAIEmbeddingProvider
  BaseVectorStore       →  FaissVectorStore | ChromaVectorStore
  BaseReranker          →  BgeReranker | NoopReranker
  BaseLLMProvider       →  OllamaProvider | OpenAIProvider | GeminiProvider | GroqProvider
                            (optionally wrapped in FallbackLLMProvider for automatic retry
                             across a configured provider chain, e.g. Groq → Gemini)
  BaseStorageProvider   →  LocalStorageProvider | (S3StorageProvider — bring your own)
```

## The RAG pipeline (`app/rag/`)

```
Retriever.retrieve()
  1. embed_query(question)                         [BaseEmbeddingProvider]
  2. vector_store.search(vector, top_k, filters)    [BaseVectorStore]
  3. reranker.rerank(question, candidates, top_k)   [BaseReranker]

PromptBuilder
  4. SYSTEM_PROMPT enforces: context-only, cite pages, exact "not found" phrase on miss
  5. build_user_prompt() interpolates ranked excerpts + optional recent chat history

RagPipeline.answer()
  6. llm.generate(prompt, system_prompt)            [BaseLLMProvider]
  7. response_formatter.format_response() strips/attaches SourceAttribution list,
     suppressing sources entirely when the model reports "not found"
```

`RagPipeline`, `Retriever`, `prompt_builder`, and `response_formatter` import **zero** vendor SDKs — verify with `grep -r "import openai\|import faiss\|import chromadb" app/rag/` (returns nothing).

## Data model

- **User** 1—N **Brochure** 1—N **Chunk** (chunk metadata mirrors what's stored alongside the vector: `car_name`, `manufacturer`, `variant`, `page_number`, `section`, `year`, `fuel_type`, `transmission`, `brochure_id`)
- **User** 1—N **ChatSession** 1—N **ChatMessage** (assistant messages store a JSON `sources` array matching `SourceAttribution`)

## Why FAISS + a relational metadata store, instead of storing everything in the vector DB

Chunk *text* lives in Postgres (`chunks.text`), not in the vector store. The vector store only holds the embedding + a small metadata dict used for filtering. This keeps the vector store interface narrow (`add/search/delete/update`) and means switching `VECTOR_DB=faiss` → `VECTOR_DB=chroma` never touches how chunk text is stored, retrieved, or displayed.

## LLM fallback chain

`get_llm_provider()` (`app/llm/factory.py`) reads `LLM_PROVIDER` (primary) and `LLM_FALLBACK_PROVIDERS` (ordered list of fallbacks). If no fallbacks are configured, it returns the bare provider directly — a misconfiguration (e.g. missing API key) fails fast and loudly at startup, which is what you want in development. If fallbacks are configured, it wraps them all in `FallbackLLMProvider` (`app/llm/fallback_provider.py`):

- `generate()` tries each provider in order, catching any exception (rate limit, timeout, auth failure) and moving to the next. Only raises if every provider in the chain fails.
- `stream()` does the same, but only *before* the first chunk has been yielded — once partial output has reached the client, a mid-stream failure is surfaced rather than silently retried (retrying risks a duplicated/corrupted answer).
- A provider that fails to *construct* (e.g. `GEMINI_API_KEY` unset) is excluded from the chain at startup rather than crashing the app, as long as at least one provider in the chain is usable.

Typical production config: `LLM_PROVIDER=groq` with `LLM_FALLBACK_PROVIDERS=["gemini"]` — free-tier Groq for speed, automatic failover to free-tier Gemini if Groq's rate limit is hit. Typical development config: `LLM_PROVIDER=ollama` with no fallbacks — fully local, no rate limits to worry about in the first place.

## Security

- Passwords hashed with bcrypt (via passlib).
- JWT access (24h default) + refresh (7d default) tokens, `HS256`, secret from `JWT_SECRET_KEY`.
- Per-IP fixed-window rate limiting middleware (`app/api/middleware.py`); swap for a Redis-backed limiter behind the same ASGI middleware interface for multi-instance deployments.
- Upload validation: extension check, PDF magic-byte check, size cap (`MAX_UPLOAD_SIZE_MB`) — see `app/utils/validation.py`.
- CORS restricted to `CORS_ORIGINS`.
