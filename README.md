# DriveWise

A production-grade, **hallucination-free** RAG (Retrieval-Augmented Generation) assistant for car brochures.

Upload one or more car brochure PDFs, ask natural-language questions, and get answers that are grounded **strictly** in the uploaded documents with page-level source attribution. If the brochure doesn't contain the answer, DriveWise says so instead of guessing.

> "I couldn't find this information in the uploaded brochure."

---

## Why DriveWise

- **Zero vendor lock-in.** Every external dependency — LLM, embeddings, vector store, PDF parser, storage — sits behind an interface. Switch providers with an environment variable, not a code change.
- **LLM fallback chain.** Configure a primary provider and one or more fallbacks (e.g. Groq → Gemini). If the primary is rate-limited or down, DriveWise automatically retries the next provider in the chain — no manual intervention, no code changes.
- **Fully local for development.** Ollama + Sentence Transformers + FAISS means you can develop the entire stack with no API keys and no data leaving your machine.
- **Grounded, cited answers.** The prompt contract forces the LLM to answer only from retrieved brochure excerpts and to cite page numbers; the response formatter attaches structured source cards.
- **Clean Architecture.** API → Service → Repository → ORM, with providers injected via interfaces. Runs directly with Python + Node — nothing to containerize, no Docker Desktop disk usage.

## Recommended provider setup

| Environment | LLM_PROVIDER | LLM_FALLBACK_PROVIDERS | Why |
|---|---|---|---|
| **Development** | `ollama` | *(none)* | Free, private, no rate limits, no internet dependency once the model is pulled |
| **Production** | `groq` | `["gemini"]` | Groq's free tier is fast; if you hit its rate limit, requests automatically retry against Gemini's free tier instead of failing |

Switching between these is a `.env` change — nothing else.

## Architecture at a glance

```
Question
   │
   ▼
Metadata Filter  ──►  Vector Search (FAISS/Chroma)  ──►  Re-ranking (BGE cross-encoder)
   │                                                            │
   ▼                                                            ▼
Prompt Builder (anti-hallucination system prompt)  ◄────────────┘
   │
   ▼
LLM (primary provider, with automatic fallback chain on failure)
   │
   ▼
Response Formatter  ──►  Answer + Source Attribution (page, section, brochure)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full component diagram and [`docs/SEQUENCE.md`](docs/SEQUENCE.md) for request-level sequence diagrams.

## Tech stack

| Layer | Choice | Swappable via |
|---|---|---|
| Backend | FastAPI, Python 3.12, async everywhere | — |
| Database | PostgreSQL + SQLAlchemy 2.0 (async) | `DATABASE_URL` |
| PDF Parsing | PyMuPDF (default), pdfplumber | `PDF_PARSER` |
| Embeddings | Sentence Transformers `BAAI/bge-small-en-v1.5` (default), OpenAI | `EMBEDDING_PROVIDER` |
| Vector Store | FAISS (default), Chroma | `VECTOR_DB` |
| Reranker | `BAAI/bge-reranker-base` cross-encoder | `RERANKER` |
| LLM | Ollama, OpenAI, Gemini, Groq — with automatic fallback chain | `LLM_PROVIDER` + `LLM_FALLBACK_PROVIDERS` |


## Quick start (local, no Docker)

### Prerequisites

- Python 3.12
- Node.js 20+
- PostgreSQL (local install, **or** a free hosted instance like [Neon](https://neon.tech) — no local install needed)
- [Ollama](https://ollama.com/download) (for local development only)

### 1. Backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set DATABASE_URL to your Postgres connection string
# (local or hosted). Defaults otherwise target Ollama for local dev.

uvicorn app.main:app --reload
```

### 2. Pull the local LLM model (development only)

```bash
ollama serve                     # run this in its own terminal, keep it running
ollama pull llama3.1:8b          # one-time download, ~4.7GB
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, register an account, upload a brochure PDF, and start asking questions.

## Switching to production providers (Groq + Gemini fallback)

Edit `.env`:

```bash
LLM_PROVIDER=groq
LLM_FALLBACK_PROVIDERS=["gemini"]
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...
```

Restart the backend. `get_llm_provider()` (`app/llm/factory.py`) builds a `FallbackLLMProvider` that tries Groq first on every request; if Groq raises an error (rate limit, timeout, outage), it automatically retries with Gemini before giving up. If you only set `LLM_PROVIDER` with no fallbacks, DriveWise uses that single provider directly with no wrapper overhead.

Same environment-only-switch pattern applies to `EMBEDDING_PROVIDER`, `VECTOR_DB`, `PDF_PARSER`, and `RERANKER`. See [`.env.example`](.env.example) for every knob.

## API surface

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Get access/refresh tokens |
| POST | `/api/v1/brochure/upload` | Upload + index a brochure PDF |
| GET | `/api/v1/brochure` | List your brochures |
| DELETE | `/api/v1/brochure/{id}` | Delete a brochure (and its vectors) |
| POST | `/api/v1/chat` | Ask a question (creates a session if none given) |
| GET | `/api/v1/chat/history` | List your chat sessions |
| GET | `/api/v1/chat/{id}` | Get a session with full message history |
| DELETE | `/api/v1/chat/{id}` | Delete a chat session |

Full interactive docs at `/docs` (Swagger) and `/redoc` once the backend is running.

## Project structure

See [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) for a full folder-by-folder walkthrough and guidance on adding a new provider (e.g. a new LLM vendor or vector store).

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — component diagram, design decisions
- [`docs/SEQUENCE.md`](docs/SEQUENCE.md) — upload flow and chat flow sequence diagrams
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — dev vs. production setup, Oracle Cloud deployment without Docker
- [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) — folder structure, how to add a new provider, coding standards

## Known simplifications (call these out honestly)

- **Migrations:** tables are created via `Base.metadata.create_all` on startup for simplicity. For real schema evolution, wire up Alembic (`alembic init`) against `app/models/models.py`'s `Base.metadata`.
- **FAISS filtering:** FAISS has no native metadata filtering, so `FaissVectorStore` over-fetches and filters in-process — fine at brochure-catalog scale, but swap to `VECTOR_DB=chroma` (native filtering) or pgvector if you're indexing millions of chunks.
- **S3 storage:** `BaseStorageProvider` is ready for an S3 implementation; only the local filesystem provider ships by default.
- **Metadata extraction:** `car_name` / `manufacturer` / `year` are guessed from the filename on upload. Swap in an LLM-based first-page extraction pass behind the same `BrochureService._index_brochure` seam if you need higher accuracy.
- **Fallback chain and streaming:** if a provider fails *after* it has already started streaming a partial answer, DriveWise surfaces the error rather than silently retrying (retrying would risk sending a duplicated or corrupted answer to the client). Full-failure fallback (the common case — rate limits, auth errors, timeouts) is handled before any output is sent.
