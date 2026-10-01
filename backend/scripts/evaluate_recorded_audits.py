"""Zero-provider regression over immutable observed M4 audit traces."""

import argparse
import asyncio
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.dataset import sha256
from app.evaluation.offline_guard import OfflineGuard
from app.evaluation.recorded_audits import FIXTURE, load_cases, replay_case


async def evaluate(*, manifest=FIXTURE, allow_unverified_prompts=False):
    frozen, cases = load_cases(manifest)
    with OfflineGuard() as guard:
        results = [await replay_case(case, allow_unverified_prompts=allow_unverified_prompts) for case in cases]
    verified = sum(item['contract_verified'] for item in results)
    return {'recorded_at': datetime.now(timezone.utc).isoformat(),
            'scope': 'observed_audit_contract_replay; not current model quality or independent legal review',
            'manifest_sha256': sha256(manifest), 'source_reports': frozen['reports'],
            'allow_unverified_prompts': allow_unverified_prompts,
            'real_model_calls': 0, 'real_model_quality_passed': None,
            'external_network_attempts': len(guard.attempts),
            'summary': {'cases': len(results), 'contracts_verified': verified,
                        'recording_mismatches': sum(item['observed'] == 'recording_mismatch' for item in results),
                        'new_guard_rejections': sum(item['current_guard_rejection'] for item in results),
                        'observed_outcomes': dict(Counter(item['observed'] for item in results))},
            'replay_contracts_passed': bool(results) and verified == len(results) and not guard.attempts,
            'results': results,
            'limitations': ['A replayed approval or rejection is an old recorded model decision, not a new legal judgment.',
                           'Changed prompt/input/order or missing old calls remain explicit mismatches; no model fallback.',
                           'Current deterministic guards can reject an old approval; these changes are reported separately.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=FIXTURE)
    parser.add_argument('--allow-unverified-prompts', action='store_true',
                        help='Explicit legacy contract replay; never validates a changed system prompt')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Choose a new output path; existing evidence is immutable')
    report = asyncio.run(evaluate(manifest=args.manifest, allow_unverified_prompts=args.allow_unverified_prompts))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('summary', 'replay_contracts_passed', 'real_model_calls')}))
    return 0 if report['replay_contracts_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
