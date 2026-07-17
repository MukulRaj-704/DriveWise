# Developer Guide

## Folder structure

```
app/
  api/            FastAPI routers (auth, brochure, chat, health) + middleware
  config/         Settings (env-driven, single source of truth)
  core/           DB session/engine, JWT + password helpers, domain exceptions
  dependencies/   DI wiring — singletons for heavy providers, get_current_user
  parser/         BasePDFParser + PyMuPDF/pdfplumber implementations + factory
  chunking/       SemanticChunker
  embeddings/     BaseEmbeddingProvider + SentenceTransformer/OpenAI implementations + factory
  vectorstore/    BaseVectorStore + FAISS/Chroma implementations + factory
  reranker/       BaseReranker + BGE cross-encoder implementation + factory
  llm/            BaseLLMProvider + Ollama/OpenAI/Gemini/Groq implementations + factory
  rag/            retriever, prompt_builder, pipeline, response_formatter — the orchestration layer
  models/         SQLAlchemy ORM models
  schemas/        Pydantic v2 request/response schemas
  repositories/   Data access layer (one repository per aggregate)
  services/       Business logic (AuthService, BrochureService, ChatService)
  utils/          Storage abstraction, upload validation
  logging/        Structured JSON logging
frontend/         React + TypeScript + Tailwind + React Query
tests/
  unit/           Pure logic: chunker, prompt builder, response formatter, security
  integration/    FAISS vector store, retriever end-to-end with fakes
  api/            Full HTTP-layer tests against an in-memory SQLite DB
```

## The golden rule: business logic never imports a vendor SDK

`app/rag/*` and `app/services/*` must only ever import from `app/*/base.py` interfaces, never `openai`, `faiss`, `chromadb`, `groq`, `google.generativeai`, etc. directly. Those imports are confined to the concrete provider modules (`*_provider.py`, `*_store.py`) and are even done lazily inside `__init__` so a deployment that never uses, say, Gemini doesn't need `google-generativeai` installed at all.

Enforce this yourself before committing:

```bash
grep -rn "^import openai\|^from openai\|^import faiss\|^import chromadb\|^import groq\|^import google.generativeai" app/rag app/services
# should print nothing
```

## How to add a new LLM provider

1. Create `app/llm/my_vendor_provider.py` implementing `BaseLLMProvider` (`generate`, `stream`).
2. Add the vendor's config fields to `Settings` (`app/config/settings.py`) — API key, model name, etc.
3. Add a branch in `_build_provider()` (`app/llm/factory.py`), and add `"my_vendor"` to the `Literal` types on `LLM_PROVIDER` / `LLM_FALLBACK_PROVIDERS`.
4. Add `LLM_PROVIDER=my_vendor` to `.env.example`. It can now also be used anywhere in a `LLM_FALLBACK_PROVIDERS` chain for free.
5. Done — no changes needed in `app/rag/pipeline.py`, `app/services/chat_service.py`, or anywhere else. `get_llm_provider()` transparently wraps it in `FallbackLLMProvider` if it's part of a chain, or returns it bare if it's the only provider configured.

The same recipe applies to embeddings (`app/embeddings/`), vector stores (`app/vectorstore/`), rerankers (`app/reranker/`), and PDF parsers (`app/parser/`) — each has the same `base.py` + concrete implementation + `factory.py` shape.

## How the ingestion pipeline extends

`BrochureService._index_brochure()` (`app/services/brochure_service.py`) is the seam for improving ingestion quality without touching anything downstream:

- Better metadata extraction (currently a filename heuristic) → replace `_guess_car_metadata()` with an LLM call over page 1, still returning the same `dict[str, str | None]` shape.
- Table-aware chunking → extend `SemanticChunker` or add a table-specific block type in `BasePDFParser`.
- OCR for scanned brochures → add a new `BasePDFParser` implementation that falls back to OCR when text extraction yields near-empty pages.

## Coding standards

- Python 3.12, type hints everywhere, Pydantic v2, SQLAlchemy 2.0 async style (`Mapped[...]`, `mapped_column`).
- Repositories only do data access (no business rules); services own business rules and call repositories + providers.
- Every new domain error should subclass `DriveWiseError` (`app/core/exceptions.py`) with a `status_code` and `default_message` — the global exception handler in `app/main.py` converts these to structured JSON automatically.
- Structured logging: use `log_event(logger, level, "event_name", **fields)` rather than f-string logging, so log lines stay machine-parseable.

## Running tests

```bash
pip install -r requirements.txt
pytest tests/unit tests/integration tests/api -q
```

The API tests spin up the FastAPI app against an in-memory SQLite DB (via `app.dependency_overrides[get_db]`), so they don't require a running Postgres instance. Integration tests exercise a real (temp-directory) FAISS index. Unit tests avoid I/O entirely.

Heavy ML dependencies (`sentence-transformers`, `torch`, real `faiss` search behavior) are exercised indirectly — the retriever test uses fake embedding/reranker implementations so the suite stays fast and doesn't require downloading model weights in CI. If you want a slow "real models" smoke test, mark it `@pytest.mark.slow` and exclude it from the default `pytest` invocation.
