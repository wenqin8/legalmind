"""Synthetic semantic probes; real configured model, no application data writes."""

import argparse
from contextlib import aclosing
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from app.agents.evidence import Evidence
from app.agents.grounding import GroundingViolation, validate_grounding
from app.core.config import Settings
from app.core.errors import ModelUnavailableError
from app.llm.factory import create_llm_client
from app.rag.catalog_profiles import profile_entries
from app.schemas.chat import SourceReference


PROBES = [
    ('omitted_exception', '用人单位解散的，但因合并或者分立',
     '用人单位解散时，法院可以认定劳动合同已经不能继续履行，不存在例外。', False),
    ('or_changed_to_and', '用人单位解散的，但因合并或者分立',
     '劳动者已与其他单位建立劳动关系时，仅在同时满足严重影响原工作且经原单位提出仍不解除这两个条件时，法院才可以认定合同不能继续履行。', False),
    ('unsupported_evidence_requirement', '营养费根据受害人伤残情况参照医疗机构的意见确定',
     '医疗意见只有明确写出营养必要性、期限和标准，才可以作为营养费认定依据。', False),
    ('omitted_contract_condition', '合同存在无效或者可撤销的情形',
     '只要当事人以合同已备案为由主张合同有效，人民法院一律不予支持，无需核对其他情形。', False),
    ('supported_conditional_rule', '营养费根据受害人伤残情况参照医疗机构的意见确定',
     '营养费根据受害人伤残情况参照医疗机构的意见确定。', True),
]


async def evaluate():
    entries = profile_entries('eval-rag-v2-209')
    settings = Settings()
    if settings.llm_backend != 'deepseek':
        raise SystemExit('Real-model probes require the configured deepseek backend')
    model = create_llm_client(settings)
    rows = []
    async with aclosing(model):
        for name, anchor, claim, expected in PROBES:
            entry = next(e for e in entries if anchor in e.verification.original_text)
            v = entry.verification
            source = SourceReference(source_type='legal_provision', source_id=uuid4(), citation_id='S1',
                title=entry.record.regulation_name, reference_number=entry.record.article_number,
                source_kind='official', is_demo=False, source_url=str(entry.record.source_url),
                version=v.version, original_text=v.original_text, effective_from=v.effective_from,
                verified_at=v.verified_at, status_as_of=v.status_as_of, applicability='general_reference')
            error = None
            try:
                await validate_grounding('结论\n' + claim, [Evidence(source, v.original_text)],
                                         '合成审核：只核对这一主张与给定原文是否一致。', model)
                supported = True
            except GroundingViolation as exc:
                supported = False
                error = exc.reason
            except ModelUnavailableError:
                supported = None
                error = 'dependency_error'
            rows.append({'id': name, 'claim': claim, 'record_id': entry.record.record_id,
                         'original_text_sha256': v.text_sha256, 'expected_supported': expected,
                         'observed_supported': supported, 'reason': error, 'passed': supported is expected})
    return {'scope': 'synthetic_development_probes_not_legal_certification', 'model': settings.deepseek_model,
            'prompt_sha256': hashlib.sha256(Path('app/agents/grounding.py').read_bytes()).hexdigest(),
            'all_passed': all(row['passed'] for row in rows), 'items': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Choose a new output path')
    report = asyncio.run(evaluate())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['all_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
