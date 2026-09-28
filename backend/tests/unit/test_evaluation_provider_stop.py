import json

import httpx
import pytest

from app.core.errors import ModelUnavailableError
from app.llm.base import LLMMessage
from scripts.evaluate_rag_answers import TraceLLM, summarize


@pytest.mark.anyio
@pytest.mark.parametrize('status', [401, 402, 403, 429, 500])
@pytest.mark.parametrize('stream_first', [False, True])
async def test_provider_auth_or_balance_failure_stops_following_calls(status, stream_first):
    class Provider:
        calls = 0
        closed = False
        async def complete(self, messages):
            self.calls += 1
            response = httpx.Response(status, request=httpx.Request('POST', 'https://example.invalid/model'),
                                      text='SECRET MUST NOT BE LOGGED')
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ModelUnavailableError() from exc
        async def stream(self, messages):
            try:
                await self.complete(messages)
                yield 'unreachable'
            finally:
                self.closed = True
    provider = Provider()
    model = TraceLLM(provider)
    messages = [LLMMessage(role='system', content='TASK:TEST'), LLMMessage(role='user', content='{}')]
    with pytest.raises(ModelUnavailableError):
        if stream_first:
            _ = [part async for part in model.stream(messages)]
        else:
            await model.complete(messages)
    with pytest.raises(ModelUnavailableError):
        await model.complete(messages)
    with pytest.raises(ModelUnavailableError):
        _ = [part async for part in model.stream(messages)]
    assert provider.calls == (1 if status in (401, 402, 403) else 3)
    assert model.calls[0]['provider_http_status'] == status
    assert 'SECRET' not in json.dumps(model.calls)
    if stream_first:
        assert provider.closed


def test_stopped_scenarios_remain_in_denominator_but_are_not_attempts():
    report = {'planned_scenarios': 2, 'scenarios': [
        {'turns': [{'status': 424, 'expected': {'expected': 'answer'}}]},
        {'turns': [{'status': None, 'error': 'provider_run_stopped', 'expected': {'expected': 'answer'}}]},
    ]}
    summarize(report)
    assert report['summary']['scenarios_attempted'] == 1
    assert report['summary']['scenarios_planned'] == 2
    assert report['summary']['behavior_match_including_errors'] == {'value': 0, 'denominator': 2}
