from app.config.settings import Settings
from app.embeddings.base import BaseEmbeddingProvider


def get_embedding_provider(settings: Settings) -> BaseEmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "openai":
        from app.embeddings.openai_embedding_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(api_key=settings.OPENAI_API_KEY)

    from app.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider

    return SentenceTransformerEmbeddingProvider(
        model_name=settings.EMBEDDING_MODEL, dimension=settings.EMBEDDING_DIMENSION
    )
