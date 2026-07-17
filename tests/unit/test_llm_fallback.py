import pytest

from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider
from app.llm.fallback_provider import FallbackLLMProvider


class FakeProvider(BaseLLMProvider):
    """A fake provider that either succeeds or always raises, for testing the chain."""

    def __init__(self, name: str, should_fail: bool = False, response: str = "ok"):
        self.name = name
        self.should_fail = should_fail
        self.response = response
        self.call_count = 0

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        self.call_count += 1
        if self.should_fail:
            raise LLMProviderError(f"{self.name} is rate-limited")
        return self.response

    async def stream(self, prompt: str, system_prompt: str | None = None):
        self.call_count += 1
        if self.should_fail:
            raise LLMProviderError(f"{self.name} is rate-limited")
        for token in self.response.split():
            yield token + " "


@pytest.mark.asyncio
async def test_generate_uses_primary_when_it_succeeds():
    primary = FakeProvider("groq", should_fail=False, response="primary answer")
    fallback = FakeProvider("gemini", should_fail=False, response="fallback answer")
    chain = FallbackLLMProvider([("groq", primary), ("gemini", fallback)])

    result = await chain.generate("question")

    assert result == "primary answer"
    assert primary.call_count == 1
    assert fallback.call_count == 0


@pytest.mark.asyncio
async def test_generate_falls_back_when_primary_fails():
    primary = FakeProvider("groq", should_fail=True)
    fallback = FakeProvider("gemini", should_fail=False, response="fallback answer")
    chain = FallbackLLMProvider([("groq", primary), ("gemini", fallback)])

    result = await chain.generate("question")

    assert result == "fallback answer"
    assert primary.call_count == 1
    assert fallback.call_count == 1


@pytest.mark.asyncio
async def test_generate_raises_when_all_providers_fail():
    primary = FakeProvider("groq", should_fail=True)
    fallback = FakeProvider("gemini", should_fail=True)
    chain = FallbackLLMProvider([("groq", primary), ("gemini", fallback)])

    with pytest.raises(LLMProviderError):
        await chain.generate("question")


@pytest.mark.asyncio
async def test_stream_falls_back_on_immediate_failure():
    primary = FakeProvider("groq", should_fail=True)
    fallback = FakeProvider("gemini", should_fail=False, response="hello world")
    chain = FallbackLLMProvider([("groq", primary), ("gemini", fallback)])

    chunks = [c async for c in chain.stream("question")]

    assert "".join(chunks).strip() == "hello world"
