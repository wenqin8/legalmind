"""Deterministic offline model used by development and tests."""

from collections.abc import AsyncIterator, Sequence

from app.llm.base import LLMClient, LLMMessage


class FakeLLMClient(LLMClient):
    def __init__(
        self,
        response: str = "这是离线假模型响应，仅用于开发与自动化测试。",
        *,
        chunk_size: int = 8,
    ) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        self.response = response
        self.chunk_size = chunk_size
        self.call_count = 0

    async def complete(self, messages: Sequence[LLMMessage]) -> str:
        del messages
        self.call_count += 1
        return self.response

    async def stream(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        del messages
        self.call_count += 1
        for index in range(0, len(self.response), self.chunk_size):
            yield self.response[index : index + self.chunk_size]
