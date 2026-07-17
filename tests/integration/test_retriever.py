from app.embeddings.base import BaseEmbeddingProvider
from app.rag.retriever import Retriever
from app.reranker.base import BaseReranker, RerankResult
from app.vectorstore.faiss_store import FaissVectorStore
from app.vectorstore.base import VectorRecord


class FakeEmbedder(BaseEmbeddingProvider):
    dimension = 4

    def embed_documents(self, texts):
        return [[1, 0, 0, 0] for _ in texts]

    def embed_query(self, text):
        return [1, 0, 0, 0]


class PassthroughReranker(BaseReranker):
    def rerank(self, query, candidates, top_k):
        return [
            RerankResult(id=c.id, text=c.text, metadata=c.metadata, score=1.0) for c in candidates[:top_k]
        ]


def test_retriever_end_to_end(tmp_path):
    store = FaissVectorStore(index_path=str(tmp_path / "idx.faiss"), dimension=4)
    store.add(
        [
            VectorRecord(id="c1", vector=[1, 0, 0, 0], metadata={"page_number": 3, "brochure_id": "b1"}),
        ]
    )

    retriever = Retriever(
        embedding_provider=FakeEmbedder(),
        vector_store=store,
        reranker=PassthroughReranker(),
        retrieval_top_k=5,
        rerank_top_k=3,
    )

    results = retriever.retrieve("what is the mileage?", chunk_texts={"c1": "Mileage is 18 km/l."})
    assert len(results) == 1
    assert results[0].chunk_id == "c1"
    assert "18 km/l" in results[0].text


def test_retriever_returns_empty_when_no_hits(tmp_path):
    store = FaissVectorStore(index_path=str(tmp_path / "idx2.faiss"), dimension=4)
    retriever = Retriever(FakeEmbedder(), store, PassthroughReranker())
    assert retriever.retrieve("anything", chunk_texts={}) == []
