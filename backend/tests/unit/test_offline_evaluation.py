import json
from pathlib import Path

import httpx
import pytest

from app.agents.tasks import extract
from app.core.config import BACKEND_DIR
from app.core.errors import ModelUnavailableError
from app.evaluation.dataset import sha256
from app.evaluation.offline_guard import OfflineGuard, OfflineNetworkError, is_loopback
from app.evaluation.replay import RecordedLLM, ReplayMismatchError, prompt_digest
from app.llm.base import LLMMessage
from app.schemas.chat import ChatRequest
from app.schemas.tasks import TaskState

pytestmark = pytest.mark.anyio


def messages(query='synthetic'):
    return [LLMMessage(role='system', content='TASK:TEST\nRules'),
            LLMMessage(role='user', content=json.dumps({'query': query}))]


def recording(**updates):
    return {'task': 'TASK:TEST', 'input': {'query': 'synthetic'}, 'output': 'ABCD',
            'system_prompt_sha256': prompt_digest(messages()[0].content), **updates}


async def test_replay_exact_call_and_original_chunks_have_no_provider():
    client = RecordedLLM([recording(chunks=['A', 'BC', 'D'])])
    assert [part async for part in client.stream(messages())] == ['A', 'BC', 'D']
    client.assert_exhausted()
    with pytest.raises(ReplayMismatchError):
        await client.complete(messages())


@pytest.mark.parametrize('change', ['query', 'prompt', 'task'])
async def test_replay_refuses_changed_request_without_falling_back(change):
    client = RecordedLLM([recording()])
    request = messages('changed' if change == 'query' else 'synthetic')
    if change in {'prompt', 'task'}:
        request[0] = LLMMessage(role='system', content='TASK:OTHER' if change == 'task' else 'TASK:TEST\nNew rules')
    with pytest.raises(ReplayMismatchError):
        await client.complete(request)
    assert client.index == 0


async def test_legacy_trace_requires_explicit_opt_in_and_does_not_verify_prompt():
    item = recording();item.pop('system_prompt_sha256')
    with pytest.raises(ReplayMismatchError):
        await RecordedLLM([item]).complete(messages())
    client = RecordedLLM([item], allow_unverified_prompt=True)
    assert await client.complete(messages()) == 'ABCD'
    assert not client.prompt_verified


async def test_replay_preserves_partial_failure_and_detects_unused_or_damaged_calls():
    client = RecordedLLM([recording(error_type='ModelUnavailableError', chunks=['AB', 'CD'])])
    parts = []
    with pytest.raises(ModelUnavailableError):
        async for part in client.stream(messages()):
            parts.append(part)
    assert parts == ['AB', 'CD']
    client.assert_exhausted()
    with pytest.raises(ReplayMismatchError):
        RecordedLLM([recording()]).assert_exhausted()
    with pytest.raises(ReplayMismatchError):
        _ = [part async for part in RecordedLLM([recording(chunks=['wrong'])]).stream(messages())]


@pytest.mark.parametrize('url', ['https://api.deepseek.com/', 'http://127.0.0.1:9999/chat/completions'])
async def test_offline_guard_blocks_http_before_any_transport_or_dns(monkeypatch, url):
    async def must_not_reach_transport(*args):
        raise AssertionError('network transport was reached')
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', must_not_reach_transport)
    with OfflineGuard() as guard:
        async with httpx.AsyncClient() as client:
            with pytest.raises(OfflineNetworkError):
                await client.get(url)
    assert len(guard.attempts) == 1
    assert is_loopback('127.0.0.1') and is_loopback('::1') and is_loopback('localhost')
    assert not is_loopback('127.0.0.1.example.com') and not is_loopback('192.0.2.1')


async def test_mock_transport_is_allowed_without_real_network():
    with OfflineGuard() as guard:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
            assert (await client.get('https://synthetic.invalid/')).status_code == 200
    assert not guard.attempts


@pytest.mark.parametrize('index', [0, 1])
async def test_real_recorded_extraction_success_and_outage_replay_current_node(index):
    fixture = json.loads((BACKEND_DIR/'data/evaluation/offline-v1/recorded-extraction.json').read_text(encoding='utf-8'))
    assert sha256(BACKEND_DIR.parent/fixture['source_report']) == fixture['source_sha256']
    case = fixture['cases'][index]
    original = json.loads((BACKEND_DIR.parent/fixture['source_report']).read_text(encoding='utf-8'))
    scenario = next(s for s in original['scenarios'] if s['id'] == case['id'])
    assert case['call'] in scenario['turns'][0]['model_trace']
    client = RecordedLLM([case['call']], allow_unverified_prompt=True)
    payload = ChatRequest(message=case['call']['input']['message'])
    if case['expected'] == 'success':
        result = await extract(payload, TaskState(kind='qa'), client)
        assert result.domain == 'marriage_family' and result.general_question
    else:
        with pytest.raises(ModelUnavailableError):
            await extract(payload, TaskState(kind='qa'), client)
    client.assert_exhausted()


def test_offline_law_metrics_use_frozen_development_labels():
    from scripts.evaluate_offline import evaluate_laws
    with OfflineGuard() as guard:
        report = evaluate_laws()
    assert len(report['results']) == 60
    assert report['direct_hit_at_5']['denominator'] == 44
    assert report['direct_hit_at_5']['value'] >= .9
    assert all(row['route'] == 'law_bm25' for row in report['results'])
    assert not guard.attempts


@pytest.mark.parametrize('module_name', ['scripts.evaluate_rag_answers', 'scripts.evaluate_grounding_probes'])
def test_live_acceptance_requires_explicit_flag_before_creating_a_model(monkeypatch, tmp_path, module_name):
    import importlib
    import sys
    module = importlib.import_module(module_name)
    def forbidden(*args, **kwargs):
        raise AssertionError('A live model was created without explicit enablement')
    monkeypatch.setattr(module, 'create_llm_client', forbidden)
    output = tmp_path / 'must-not-exist.json'
    monkeypatch.setattr(sys, 'argv', [module_name, '--output', str(output)])
    with pytest.raises(SystemExit, match='allow-real-model'):
        module.main()
    assert not output.exists()
