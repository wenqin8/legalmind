"""Replay observed support/condition decisions without predicting new model output."""

import json
from pathlib import Path

from app.agents.evidence import Evidence, validate_citations
from app.agents.grounding import GroundingViolation, validate_grounding
from app.core.config import BACKEND_DIR
from app.core.errors import ModelUnavailableError
from app.evaluation.dataset import sha256
from app.evaluation.replay import RecordedLLM, ReplayMismatchError
from app.schemas.chat import SourceReference

FIXTURE = BACKEND_DIR / 'data/evaluation/offline-m4-v1/manifest.json'


def load_cases(manifest_path=FIXTURE):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    root = BACKEND_DIR.parent
    cases = []
    for name, expected_hash in manifest['reports'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or sha256(path) != expected_hash:
            raise ValueError('Recorded audit source fingerprint mismatch')
        report = json.loads(path.read_text(encoding='utf-8'))
        for scenario in report['scenarios']:
            for turn_number, turn in enumerate(scenario['turns'], 1):
                trace = turn.get('model_trace', [])
                sources = {item['source']['citation_id']: item['source']
                           for call in trace if call['task'] == 'TASK:APPLICABILITY'
                           for item in call['input']['candidates']}
                for index, call in enumerate(trace):
                    if call['task'] != 'TASK:GROUNDING':
                        continue
                    calls = [call]
                    if (index + 1 < len(trace) and trace[index + 1]['task'] == 'TASK:CONDITIONS'
                            and trace[index + 1]['input'] == call['input']):
                        calls.append(trace[index + 1])
                    payload = call['input']
                    evidence = []
                    for item in payload['evidence']:
                        source = SourceReference.model_validate(sources[item['citation_id']])
                        if item['text'] != source.original_text:
                            raise ValueError('Recorded audit does not contain the complete selected original')
                        evidence.append(Evidence(source, item['text']))
                    provider_error = any(c.get('error_type') for c in calls)
                    rejected = any(item['verdict'] == 'unsupported' for c in calls
                                   if not c.get('error_type') for item in json.loads(c['output'])['items'])
                    # Some old paths returned after the support audit and never
                    # recorded the independent condition audit. Do not invent it.
                    cases.append({'id': f'{Path(name).stem}:{scenario["id"]}:{turn_number}:{index}',
                                  'source_report': name, 'scenario': scenario['id'], 'turn': turn_number,
                                  'calls': calls, 'payload': payload, 'evidence': evidence,
                                  'expected': 'provider_error' if provider_error else ('rejected' if rejected else 'accepted'),
                                  'condition_audit_recorded': len(calls) == 2})
    return manifest, cases


async def replay_case(case, *, allow_unverified_prompts=False):
    # Explicit contract mode ignores only old system prompt hashes. Input,
    # task, order, output and source snapshots remain exact; no provider exists.
    calls = [{k: v for k, v in call.items() if k != 'system_prompt_sha256'}
             for call in case['calls']] if allow_unverified_prompts else case['calls']
    client = RecordedLLM(calls, allow_unverified_prompt=allow_unverified_prompts)
    payload = case['payload']
    reason = None
    mismatch = None
    try:
        rendered = await validate_grounding(payload['paragraph'], case['evidence'], payload['query'],
                                             client, payload.get('validated_context', ''))
        validate_citations(rendered, case['evidence'])
        observed = 'accepted'
    except GroundingViolation as exc:
        observed, reason = 'rejected', exc.reason
    except ReplayMismatchError as exc:
        observed, mismatch = 'recording_mismatch', str(exc)
    except ModelUnavailableError:
        observed = 'provider_error'
    current_guard = observed == 'rejected' and client.index == 0
    exact_result = observed == case['expected'] and client.index == len(calls)
    return {'id': case['id'], 'source_report': case['source_report'], 'scenario': case['scenario'],
            'turn': case['turn'], 'recorded': case['expected'], 'observed': observed,
            'reason': reason, 'recorded_calls': len(calls), 'consumed_calls': client.index,
            'prompt_verified': client.prompt_verified, 'condition_audit_recorded': case['condition_audit_recorded'],
            'mismatch': mismatch,
            'current_guard_rejection': current_guard, 'exact_recorded_outcome': exact_result,
            'contract_verified': exact_result or current_guard}
