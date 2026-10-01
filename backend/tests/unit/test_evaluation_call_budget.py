"""Paid inference has a hard cap across stream/complete, including failed calls."""

import pytest

from app.core.errors import ModelUnavailableError
from app.llm.base import LLMMessage
from scripts.evaluate_rag_answers import TraceLLM

MESSAGES = [LLMMessage(role='system', content='TASK:TEST'), LLMMessage(role='user', content='{}')]


class CountingProvider:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    async def complete(self, messages):
        self.calls += 1
        if self.fail:
            raise ModelUnavailableError()
        return '{}'

    async def stream(self, messages):
        yield await self.complete(messages)


@pytest.mark.anyio
@pytest.mark.parametrize('fail', [False, True])
@pytest.mark.parametrize('stream_first', [False, True])
async def test_cap_counts_all_attempts_and_never_starts_a_following_provider_call(fail, stream_first):
    provider = CountingProvider(fail)
    client = TraceLLM(provider, max_model_calls=1)
    if fail:
        with pytest.raises(ModelUnavailableError):
            if stream_first:
                _ = [part async for part in client.stream(MESSAGES)]
            else:
                await client.complete(MESSAGES)
    elif stream_first:
        assert [part async for part in client.stream(MESSAGES)] == ['{}']
    else:
        assert await client.complete(MESSAGES) == '{}'
    assert not client.call_limit_reached
    for streaming in (True, False):
        with pytest.raises(ModelUnavailableError):
            if streaming:
                _ = [part async for part in client.stream(MESSAGES)]
            else:
                await client.complete(MESSAGES)
    assert client.call_limit_reached
    assert provider.calls == len(client.calls) == 1


@pytest.mark.parametrize('limit', [0, -1, True])
def test_invalid_call_limit_is_rejected(limit):
    with pytest.raises(ValueError, match='positive'):
        TraceLLM(CountingProvider(), max_model_calls=limit)


@pytest.mark.parametrize('limit', ['0', '-1'])
def test_invalid_cli_budget_never_consumes_a_once_package_or_creates_provider(monkeypatch, tmp_path, limit):
    import sys
    import scripts.evaluate_rag_answers as module
    def forbidden(*args, **kwargs):
        raise AssertionError('Invalid budget must fail before preparation')
    monkeypatch.setattr(module, 'create_llm_client', forbidden)
    monkeypatch.setattr(module, 'prepare', forbidden)
    monkeypatch.setattr(sys, 'argv', ['evaluate_rag_answers', '--allow-real-model', '--max-model-calls', limit,
                                    '--acceptance-package', str(tmp_path), '--output', str(tmp_path/'report.json')])
    with pytest.raises(SystemExit, match='must be positive'):
        module.main()
    assert not (tmp_path/'report.json').exists()
    assert not (tmp_path/'observation-receipt.json').exists()


def test_once_package_requires_explicit_budget_before_any_preparation(monkeypatch, tmp_path):
    import sys
    import scripts.evaluate_rag_answers as module
    def forbidden(*args, **kwargs):
        raise AssertionError('Missing explicit once budget must fail before preparation')
    monkeypatch.setattr(module, 'create_llm_client', forbidden)
    monkeypatch.setattr(module, 'prepare', forbidden)
    monkeypatch.setattr(sys, 'argv', ['evaluate_rag_answers', '--allow-real-model',
                                    '--acceptance-package', str(tmp_path), '--output', str(tmp_path/'report.json')])
    with pytest.raises(SystemExit, match='explicit --max-model-calls'):
        module.main()
    assert not (tmp_path/'report.json').exists()
    assert not (tmp_path/'observation-receipt.json').exists()
