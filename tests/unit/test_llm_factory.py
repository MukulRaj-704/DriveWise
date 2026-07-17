from app.config.settings import Settings
from app.llm.factory import get_llm_provider
from app.llm.fallback_provider import FallbackLLMProvider
from app.llm.ollama_provider import OllamaProvider


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


def test_single_provider_returns_bare_instance_no_fallback_wrapper():
    settings = _settings(LLM_PROVIDER="ollama", LLM_FALLBACK_PROVIDERS=[])
    provider = get_llm_provider(settings)
    assert isinstance(provider, OllamaProvider)
    assert not isinstance(provider, FallbackLLMProvider)


def test_fallback_chain_is_built_when_configured():
    settings = _settings(
        LLM_PROVIDER="ollama",
        LLM_FALLBACK_PROVIDERS=["ollama"],  # duplicate on purpose to test de-dup
        OLLAMA_BASE_URL="http://localhost:11434",
    )
    provider = get_llm_provider(settings)
    # Duplicate primary/fallback should collapse to a single provider (no wrapper needed).
    assert isinstance(provider, OllamaProvider)


def test_unconfigured_fallback_provider_is_skipped_not_fatal():
    # gemini has no API key configured -> should be excluded from the chain,
    # not crash startup, as long as at least one provider in the chain works.
    settings = _settings(
        LLM_PROVIDER="ollama",
        LLM_FALLBACK_PROVIDERS=["gemini"],
        GEMINI_API_KEY="",
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, FallbackLLMProvider)
    names = [name for name, _ in provider.providers]
    assert names == ["ollama"]
