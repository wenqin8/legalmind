import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import ModelUnavailableError
from app.llm.base import LLMMessage
from app.llm.deepseek import DeepSeekLLMClient
from app.llm.factory import create_llm_client
from app.llm.fake import FakeLLMClient

MESSAGES = [LLMMessage(role="user", content="test message")]


def _deepseek_client(
    http_client: httpx.AsyncClient,
    *,
    api_key: SecretStr | None = SecretStr("test-key"),
    thinking_enabled: bool = False,
) -> DeepSeekLLMClient:
    return DeepSeekLLMClient(
        base_url="https://api.deepseek.com",
        api_key=api_key,
        model="deepseek-v4-flash",
        thinking_enabled=thinking_enabled,
        timeout_seconds=10,
        temperature=0.2,
        max_tokens=256,
        http_client=http_client,
    )


def test_fake_llm_is_deterministic_and_streamable() -> None:
    async def scenario() -> None:
        client = FakeLLMClient(response="abcdefghij", chunk_size=3)

        assert await client.complete(MESSAGES) == "abcdefghij"
        chunks = [chunk async for chunk in client.stream(MESSAGES)]

        assert chunks == ["abc", "def", "ghi", "j"]
        assert "".join(chunks) == "abcdefghij"
        assert client.call_count == 2

    asyncio.run(scenario())


def test_factory_selects_fake_without_network() -> None:
    settings = Settings(_env_file=None, llm_backend="fake")

    assert isinstance(create_llm_client(settings), FakeLLMClient)


def test_deepseek_complete_uses_openai_compatible_contract() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/chat/completions"
            assert request.headers["Authorization"] == "Bearer test-key"
            payload = json.loads(request.content)
            assert payload["model"] == "deepseek-v4-flash"
            assert payload["messages"] == [
                {"role": "user", "content": "test message"}
            ]
            assert payload["stream"] is False
            assert payload["thinking"] == {"type": "disabled"}
            assert payload["temperature"] == 0.2
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {"content": "model answer"},
                            "finish_reason": "stop",
                        }
                    ]
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.deepseek.com",
        ) as http_client:
            client = _deepseek_client(http_client)
            assert await client.complete(MESSAGES) == "model answer"

    asyncio.run(scenario())


def test_deepseek_stream_parses_sse_deltas() -> None:
    async def scenario() -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            body = (
                'data: {"choices":[{"delta":{"content":"hello "},"finish_reason":null}]}\n\n'
                'data: {"choices":[{"delta":{"content":"world"},"finish_reason":null}]}\n\n'
                'data: {"choices":[{"delta":{"content":""},"finish_reason":"stop"}]}\n\n'
                "data: [DONE]\n\n"
            )
            return httpx.Response(200, text=body)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.deepseek.com",
        ) as http_client:
            client = _deepseek_client(http_client)
            chunks = [chunk async for chunk in client.stream(MESSAGES)]
            assert chunks == ["hello ", "world"]

    asyncio.run(scenario())


def test_deepseek_thinking_mode_omits_ineffective_temperature() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert payload["thinking"] == {"type": "enabled"}
            assert "temperature" not in payload
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {"content": "model answer"},
                            "finish_reason": "stop",
                        }
                    ]
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.deepseek.com",
        ) as http_client:
            client = _deepseek_client(http_client, thinking_enabled=True)
            assert await client.complete(MESSAGES) == "model answer"

    asyncio.run(scenario())


@pytest.mark.parametrize("status_code", [401, 429, 500])
def test_deepseek_http_failures_are_sanitized(status_code: int) -> None:
    async def scenario() -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, text="upstream-secret-detail")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.deepseek.com",
        ) as http_client:
            client = _deepseek_client(http_client)
            with pytest.raises(ModelUnavailableError) as exc_info:
                await client.complete(MESSAGES)
            assert "upstream-secret-detail" not in str(exc_info.value)

    asyncio.run(scenario())


def test_deepseek_missing_key_fails_only_when_called() -> None:
    async def scenario() -> None:
        async with httpx.AsyncClient(base_url="https://api.deepseek.com") as http_client:
            client = _deepseek_client(http_client, api_key=None)
            with pytest.raises(ModelUnavailableError):
                await client.complete(MESSAGES)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "finish_reason", ["length", "content_filter", "insufficient_system_resource"]
)
def test_deepseek_rejects_incomplete_non_stream_response(
    finish_reason: str,
) -> None:
    async def scenario() -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {"content": "partial answer"},
                            "finish_reason": finish_reason,
                        }
                    ]
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.deepseek.com",
        ) as http_client:
            client = _deepseek_client(http_client)
            with pytest.raises(ModelUnavailableError):
                await client.complete(MESSAGES)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "body",
    [
        'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":null}]}\n\n',
        (
            'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":null}]}\n\n'
            'data: {"choices":[{"delta":{"content":""},"finish_reason":"length"}]}\n\n'
            "data: [DONE]\n\n"
        ),
        (
            'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":null}]}\n\n'
            "data: [DONE]\n\n"
        ),
        (
            'data: {"choices":[{"delta":{"content":""},"finish_reason":"stop"}]}\n\n'
            "data: [DONE]\n\n"
        ),
        (
            'data: {"choices":[{"delta":null,"finish_reason":"stop"}]}\n\n'
            "data: [DONE]\n\n"
        ),
    ],
)
def test_deepseek_rejects_incomplete_stream(body: str) -> None:
    async def scenario() -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=body)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.deepseek.com",
        ) as http_client:
            client = _deepseek_client(http_client)
            with pytest.raises(ModelUnavailableError):
                _ = [chunk async for chunk in client.stream(MESSAGES)]

    asyncio.run(scenario())
