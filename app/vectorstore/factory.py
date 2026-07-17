from app.config.settings import Settings
from app.vectorstore.base import BaseVectorStore


def get_vector_store(settings: Settings) -> BaseVectorStore:
    if settings.VECTOR_DB == "chroma":
        from app.vectorstore.chroma_store import ChromaVectorStore

        return ChromaVectorStore(persist_dir=settings.CHROMA_PERSIST_DIR)

    from app.vectorstore.faiss_store import FaissVectorStore

    return FaissVectorStore(index_path=settings.FAISS_INDEX_PATH, dimension=settings.EMBEDDING_DIMENSION)
