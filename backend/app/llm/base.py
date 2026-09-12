"""Provider-independent asynchronous LLM contract."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: Literal["system", "user", "assistant"]
    content: str


class LLMClient(ABC):
    """The only model interface used by application and Agent code."""

    @abstractmethod
    async def complete(self, messages: Sequence[LLMMessage]) -> str:
        """Return one complete assistant message."""

    @abstractmethod
    async def stream(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        """Yield assistant text deltas in order."""
        if False:  # pragma: no cover - makes this an async-generator contract
            yield ""

    async def aclose(self) -> None:
        """Release optional network resources."""
