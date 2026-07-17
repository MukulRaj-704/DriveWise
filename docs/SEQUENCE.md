# Sequence Diagrams

## 1. Brochure upload & indexing

```
User          Frontend        FastAPI          BrochureService     Parser/Chunker/Embedder    VectorStore    Postgres
 │  select PDF   │                │                    │                     │                    │             │
 │──────────────►│                │                    │                     │                    │             │
 │               │ POST /brochure/upload (multipart)   │                     │                    │             │
 │               │───────────────►│                    │                     │                    │             │
 │               │                │ validate_pdf_upload()                    │                    │             │
 │               │                │ storage.save(bytes) ──────────────────────────────────────────────────────► │(file on disk)
 │               │                │ brochure_repo.create(status=processing)  │                    │             │
 │               │                │────────────────────────────────────────────────────────────────────────────►│ INSERT brochures
 │               │                │ _index_brochure(brochure)                │                    │             │
 │               │                │                    │ parser.parse(path) │                    │             │
 │               │                │                    │────────────────────►                    │             │
 │               │                │                    │◄──────────────────── ParsedDocument      │             │
 │               │                │                    │ chunker.chunk(blocks)                    │             │
 │               │                │                    │────────────────────►                    │             │
 │               │                │                    │◄──────────────────── SemanticChunk[]     │             │
 │               │                │                    │ embedder.embed_documents(texts)          │             │
 │               │                │                    │────────────────────►                    │             │
 │               │                │                    │◄──────────────────── vector[]            │             │
 │               │                │                    │ chunk_repo.bulk_create(Chunk rows) ───────────────────►│ INSERT chunks
 │               │                │                    │ vector_store.add(VectorRecord[]) ────────► index.add   │
 │               │                │ brochure_repo.update_status(ready, page_count) ───────────────────────────►│ UPDATE brochures
 │               │◄───────────────│ 201 BrochureOut (status=ready)           │                    │             │
 │◄──────────────│                │                    │                     │                    │             │
```

If parsing/embedding/indexing throws at any step, `BrochureService.upload` catches it, marks the brochure `status=failed` with `error_message`, and re-raises a `ParsingError` (mapped to HTTP 422 by the global exception handler) — the brochure row is kept (not silently dropped) so the failure is visible in the Library page.

## 2. Chat / question answering

```
User        Frontend        FastAPI         ChatService       Retriever      VectorStore   Reranker      LLMProvider    Postgres
 │  ask Q      │                │                 │                │              │            │              │             │
 │────────────►│                │                 │                │              │            │              │             │
 │             │ POST /chat {message, session_id?} │                │              │            │              │             │
 │             │───────────────►│                  │                │              │            │              │             │
 │             │                │ get_current_user(JWT)              │              │            │              │             │
 │             │                │ ChatService.ask(user_id, req)      │              │            │              │             │
 │             │                │                 │ [new session?] chat_repo.create_session ─────────────────────────────────►│ INSERT chat_sessions
 │             │                │                 │ list ready brochures + chunk_texts for user ──────────────────────────────►│ SELECT
 │             │                │                 │ chat_repo.add_message(role=user) ─────────────────────────────────────────►│ INSERT chat_messages
 │             │                │                 │ RagPipeline.answer(question, chunk_texts, filters, history)               │             │
 │             │                │                 │────────────────►│                │            │              │             │
 │             │                │                 │                 │ embed_query(question)        │            │              │             │
 │             │                │                 │                 │ vector_store.search(vec, top_k, filters) ─►│            │              │             │
 │             │                │                 │                 │◄──────────────── hits          │            │              │             │
 │             │                │                 │                 │ reranker.rerank(question, candidates) ────►│            │              │             │
 │             │                │                 │                 │◄────────────────────────────────────────── ranked chunks│              │             │
 │             │                │                 │◄──────────────── RetrievedChunk[]              │            │              │             │
 │             │                │                 │ [empty?] → short-circuit "not found", skip LLM call         │              │             │
 │             │                │                 │ build_user_prompt(question, chunks, history)                 │              │             │
 │             │                │                 │ llm.generate(prompt, SYSTEM_PROMPT) ─────────────────────────────────────►│              │
 │             │                │                 │◄──────────────────────────────────────────────────────────── raw_answer │              │
 │             │                │                 │ format_response(raw_answer, chunks, brochure_names)          │              │             │
 │             │                │                 │ chat_repo.add_message(role=assistant, sources=[...]) ────────────────────────────────────►│ INSERT chat_messages
 │             │◄───────────────│ 200 {session_id, answer, sources[]}                                            │              │             │
 │◄────────────│  render answer + source cards                                                                    │              │             │
```

Key anti-hallucination checkpoint: if retrieval returns zero chunks, `RagPipeline.answer()` returns the fixed "not found" message **without ever calling the LLM** — no vendor call, no chance of the model inventing an answer from parametric knowledge.
