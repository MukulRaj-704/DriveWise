"""Optional Google Gemini LLM provider. Only imported/instantiated when LLM_PROVIDER=gemini."""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    def __init__(
        self, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.1, max_tokens: int = 1024
    ):
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover
            raise LLMProviderError("google-generativeai package is not installed.") from exc

        if not api_key:
            raise LLMProviderError("GEMINI_API_KEY is required for the gemini provider.")

        genai.configure(api_key=api_key)
        self._genai = genai
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_model(self, system_prompt: str | None):
        return self._genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            },
        )

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            model = self._build_model(system_prompt)
            response = await model.generate_content_async(prompt)
            return (response.text or "").strip()
        except Exception as exc:
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc

    async def stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        try:
            model = self._build_model(system_prompt)
            response = await model.generate_content_async(prompt, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            raise LLMProviderError(f"Gemini streaming request failed: {exc}") from exc
