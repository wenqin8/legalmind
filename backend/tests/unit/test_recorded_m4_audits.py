"""Immutable real traces exercise current orchestration with zero paid calls."""

import json

import pytest

from app.agents.grounding import GroundingViolation
from app.agents.qa import checked_paragraph
from app.evaluation.offline_guard import OfflineGuard
from app.evaluation.recorded_audits import load_cases, replay_case
from app.evaluation.replay import RecordedLLM, ReplayMismatchError

_, CASES = load_cases()


@pytest.mark.anyio
@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
async def test_observed_audit_contracts_and_incomplete_old_recordings(case):
    with OfflineGuard() as guard:
        result = await replay_case(case, allow_unverified_prompts=True)
    assert not guard.attempts
    assert not result['prompt_verified']
    if case['id'] == 'm4-real-development-20261001-run3:E-L-CD-05:2:3':
        # The old implementation stopped at a partial first-review failure.
        # Today's second review has no recorded output; never fabricate one.
        assert result['observed'] == 'recording_mismatch'
        assert result['mismatch'] == 'No recorded response; replay never calls a provider'
        assert result['consumed_calls'] == 1
        assert not result['contract_verified']
    else:
        assert result['contract_verified'], result


@pytest.mark.anyio
async def test_latest_old_repair_is_not_reused_after_the_current_guard_changes_its_input():
    first = next(case for case in CASES if case['id'] == 'm4-real-development-20261001-run11:E-L-MF-04:1:6')
    final = next(case for case in CASES if case['id'] == 'm4-real-development-20261001-run11:E-L-MF-04:1:9')
    from app.core.config import BACKEND_DIR
    report = json.loads((BACKEND_DIR.parent / first['source_report']).read_text(encoding='utf-8'))
    turn = next(s for s in report['scenarios'] if s['id'] == 'E-L-MF-04')['turns'][0]
    revision = turn['model_trace'][8]
    client = RecordedLLM([*first['calls'], revision, *final['calls']])
    payload = first['payload']
    with OfflineGuard() as guard, pytest.raises(ReplayMismatchError, match='task or input differs'):
        await checked_paragraph(payload['paragraph'], first['evidence'], payload['query'], client,
                                payload['validated_context'])
    assert not guard.attempts
    # The original overbroad property claim now fails before either model audit.
    # Current repair feedback/task no longer matches the preserved old trace.
    # Do not fabricate a new model response or assert old outputs test new prompts.
    assert client.index == 0


@pytest.mark.anyio
async def test_changed_input_and_prompt_are_not_silently_accepted():
    case = next(case for case in CASES if case['id'] == 'm4-real-development-20261001-run11:E-L-MF-01:1:4')
    changed = {**case, 'payload': {**case['payload'], 'query': 'changed input'}}
    result = await replay_case(changed)
    assert result['observed'] == 'recording_mismatch' and result['consumed_calls'] == 0
    changed_calls = [{**case['calls'][0], 'system_prompt_sha256': '0' * 64}, *case['calls'][1:]]
    result = await replay_case({**case, 'calls': changed_calls})
    assert result['observed'] == 'recording_mismatch' and result['consumed_calls'] == 0


def test_source_report_tampering_is_rejected_before_replay(tmp_path):
    from app.evaluation.recorded_audits import FIXTURE
    manifest = json.loads(FIXTURE.read_text(encoding='utf-8'))
    manifest['reports'][next(iter(manifest['reports']))] = '0' * 64
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='fingerprint'):
        load_cases(path)
