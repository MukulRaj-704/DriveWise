"""Fallback LLM provider — tries a primary provider, and on failure (rate
limit, outage, timeout, missing API key, etc.) automatically retries with
the next provider in a configured chain.

This is what makes "develop against Ollama, deploy against Groq with a
Gemini fallback" possible purely through configuration:

    LLM_PROVIDER=groq
    LLM_FALLBACK_PROVIDERS=["gemini"]

`RagPipeline` and every other caller still only see a single `BaseLLMProvider`
— they have no idea a fallback chain exists underneath.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider
from app.logging.logger import get_logger, log_event

logger = get_logger(__name__)


class FallbackLLMProvider(BaseLLMProvider):
    def __init__(self, providers: list[tuple[str, BaseLLMProvider]]):
        """`providers` is an ordered list of (name, provider) pairs; the first
        entry is the primary, the rest are fallbacks tried in order."""
        if not providers:
            raise ValueError("FallbackLLMProvider requires at least one provider.")
        self.providers = providers

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        last_error: Exception | None = None

        for name, provider in self.providers:
            try:
                result = await provider.generate(prompt, system_prompt)
                if last_error is not None:
                    log_event(logger, 30, "llm_fallback_succeeded", provider=name)
                return result
            except Exception as exc:  # noqa: BLE001 - intentionally broad: any provider failure should trigger fallback
                last_error = exc
                log_event(logger, 30, "llm_provider_failed", provider=name, error=str(exc))
                continue

        raise LLMProviderError(
            f"All LLM providers failed. Last error: {last_error}"
        ) from last_error

    async def stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        last_error: Exception | None = None

        for name, provider in self.providers:
            try:
                # Buffer the first chunk before yielding anything, so that if this
                # provider fails immediately (e.g. auth/rate-limit error surfaced
                # on the first request) we can still cleanly fall back to the next
                # provider without having sent a partial response to the client.
                chunks = provider.stream(prompt, system_prompt)
                first_chunk = await chunks.__anext__()
            except StopAsyncIteration:
                continue  # provider returned nothing; try the next one
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                log_event(logger, 30, "llm_provider_failed", provider=name, error=str(exc))
                continue

            if last_error is not None:
                log_event(logger, 30, "llm_fallback_succeeded", provider=name)

            yield first_chunk
            try:
                async for chunk in chunks:
                    yield chunk
            except Exception as exc:  # noqa: BLE001
                # Failure mid-stream: we've already sent partial output to the
                # client, so we can't silently retry on a different provider.
                # Surface the error rather than risk a corrupted/duplicated answer.
                log_event(logger, 40, "llm_provider_failed_mid_stream", provider=name, error=str(exc))
                raise LLMProviderError(f"{name} failed mid-stream: {exc}") from exc
            return

        raise LLMProviderError(
            f"All LLM providers failed. Last error: {last_error}"
        ) from last_error
