"""
get_llm_provider() is the ONLY place in the codebase that knows which
concrete LLM SDK is being used. Switching providers — or configuring a
fallback chain — is a pure environment-variable change, no application
code changes required.

Examples:
    # Local development: Ollama only, no fallback.
    LLM_PROVIDER=ollama

    # Production: Groq primary, Gemini fallback if Groq is rate-limited/down.
    LLM_PROVIDER=groq
    LLM_FALLBACK_PROVIDERS=["gemini"]
"""
from app.config.settings import Settings
from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider


def _build_provider(provider_name: str, settings: Settings) -> BaseLLMProvider:
    """Instantiate a single named provider. Raises LLMProviderError if the
    provider is misconfigured (e.g. missing API key) — callers building a
    fallback chain catch this per-provider so one bad config doesn't break
    the whole chain."""
    if provider_name == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    if provider_name == "openai":
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    if provider_name == "groq":
        from app.llm.groq_provider import GroqProvider

        return GroqProvider(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    if provider_name == "gemini":
        from app.llm.gemini_provider import GeminiProvider

        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    raise LLMProviderError(f"Unknown LLM provider: {provider_name}")


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    provider_names = [settings.LLM_PROVIDER, *settings.LLM_FALLBACK_PROVIDERS]

    # De-duplicate while preserving order (e.g. avoid building "groq" twice if
    # someone accidentally lists it as both primary and fallback).
    seen: set[str] = set()
    ordered_names = [n for n in provider_names if not (n in seen or seen.add(n))]

    if len(ordered_names) == 1:
        # No fallback configured — return the provider directly so a
        # misconfiguration (e.g. missing API key) fails fast and loudly at
        # startup instead of being silently swallowed by a fallback chain.
        return _build_provider(ordered_names[0], settings)

    built: list[tuple[str, BaseLLMProvider]] = []
    errors: list[str] = []
    for name in ordered_names:
        try:
            built.append((name, _build_provider(name, settings)))
        except LLMProviderError as exc:
            # A provider in the fallback chain being unconfigured (e.g. no
            # GEMINI_API_KEY set) shouldn't prevent startup — just exclude it
            # from the chain.
            errors.append(f"{name}: {exc}")

    if not built:
        raise LLMProviderError(
            "No LLM provider in the chain could be initialized. " + "; ".join(errors)
        )

    from app.llm.fallback_provider import FallbackLLMProvider

    return FallbackLLMProvider(built)
