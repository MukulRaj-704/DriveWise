"""Optional Groq LLM provider (OpenAI-compatible API, very fast inference).
Only imported/instantiated when LLM_PROVIDER=groq."""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    def __init__(
        self, api_key: str, model: str = "llama-3.1-8b-instant", temperature: float = 0.1, max_tokens: int = 1024
    ):
        try:
            from groq import AsyncGroq
        except ImportError as exc:  # pragma: no cover
            raise LLMProviderError("groq package is not installed.") from exc

        if not api_key:
            raise LLMProviderError("GROQ_API_KEY is required for the groq provider.")

        self._client = AsyncGroq(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _messages(self, prompt: str, system_prompt: str | None) -> list[dict]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=self._messages(prompt, system_prompt),
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            raise LLMProviderError(f"Groq request failed: {exc}") from exc

    async def stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=self._messages(prompt, system_prompt),
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            raise LLMProviderError(f"Groq streaming request failed: {exc}") from exc
