from app.config.settings import Settings
from app.reranker.base import BaseReranker


def get_reranker(settings: Settings) -> BaseReranker:
    if settings.RERANKER == "none":
        from app.reranker.bge_reranker import NoopReranker

        return NoopReranker()

    from app.reranker.bge_reranker import BgeReranker

    return BgeReranker(model_name=settings.RERANKER_MODEL)
