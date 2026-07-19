"""Google Gemini provider using the new google-genai SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ):
        if not api_key:
            raise LLMProviderError(
                "GEMINI_API_KEY is required for the gemini provider."
            )

        self.client = genai.Client(api_key=api_key)
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        print(">>> GEMINI GENERATE CALLED <<<")
        try:
            contents = prompt
            if system_prompt:
                contents = f"{system_prompt}\n\n{prompt}"

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
            )

            return response.text or ""

        except Exception as exc:
            print("=" * 100)
            print("GEMINI ERROR")
            print(type(exc))
            print(exc)
            traceback.print_exc()
            print("=" * 100)
            raise
        
    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        try:
            contents = prompt
            if system_prompt:
                contents = f"{system_prompt}\n\n{prompt}"

            async for chunk in self.client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                ),
            ):
                if chunk.text:
                    yield chunk.text

        except Exception as exc:
            raise LLMProviderError(
                f"Gemini streaming request failed: {exc}"
            ) from exc