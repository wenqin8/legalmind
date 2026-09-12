"""DeepSeek OpenAI-compatible chat-completions adapter."""

import json
from collections.abc import AsyncIterator, Mapping, Sequence

import httpx
from pydantic import SecretStr

from app.core.errors import ModelUnavailableError
from app.llm.base import LLMClient, LLMMessage


class DeepSeekLLMClient(LLMClient):
    """A lazy network adapter with sanitized failure behavior."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: SecretStr | None,
        model: str,
        thinking_enabled: bool,
        timeout_seconds: float,
        temperature: float,
        max_tokens: int,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.thinking_enabled = thinking_enabled
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
        )

    def _headers(self) -> dict[str, str]:
        key = self.api_key.get_secret_value().strip() if self.api_key else ""
        if not key:
            raise ModelUnavailableError()
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _payload(
        self, messages: Sequence[LLMMessage], *, stream: bool
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "max_tokens": self.max_tokens,
            "stream": stream,
            "thinking": {
                "type": "enabled" if self.thinking_enabled else "disabled"
            },
        }
        if not self.thinking_enabled:
            payload["temperature"] = self.temperature
        return payload

    @staticmethod
    def _first_choice(payload: object) -> Mapping[str, object]:
        if not isinstance(payload, Mapping):
            raise ValueError("Invalid model response")
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Invalid model choices")
        choice = choices[0]
        if not isinstance(choice, Mapping):
            raise ValueError("Invalid model choice")
        return choice

    async def complete(self, messages: Sequence[LLMMessage]) -> str:
        try:
            response = await self._client.post(
                "/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, stream=False),
            )
            response.raise_for_status()
            payload = response.json()
            choice = self._first_choice(payload)
            if choice.get("finish_reason") != "stop":
                raise ValueError("Model response did not finish normally")
            message = choice.get("message")
            if not isinstance(message, Mapping):
                raise ValueError("Invalid model message")
            content = message.get("content")
            if not isinstance(content, str) or not content:
                raise ValueError("Missing model content")
            return content
        except ModelUnavailableError:
            raise
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            raise ModelUnavailableError() from exc

    async def stream(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        saw_content = False
        saw_stop = False
        saw_done = False
        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, stream=True),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        saw_done = True
                        break
                    payload = json.loads(data)
                    choice = self._first_choice(payload)
                    finish_reason = choice.get("finish_reason")
                    if finish_reason is not None:
                        if finish_reason != "stop":
                            raise ModelUnavailableError()
                        saw_stop = True
                    delta = choice.get("delta")
                    if not isinstance(delta, Mapping):
                        raise ValueError("Invalid model delta")
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        saw_content = True
                        yield content
                if not saw_content or not saw_stop or not saw_done:
                    raise ModelUnavailableError()
        except ModelUnavailableError:
            raise
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            raise ModelUnavailableError() from exc

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
