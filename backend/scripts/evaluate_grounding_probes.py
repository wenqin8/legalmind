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
    ('inherited_condition', '合同存在无效或者可撤销的情形',
     '在前述合同存在无效或者可撤销情形的范围内，不能仅以已办理批准、登记等手续或者备案为由主张合同有效。', True),
    ('context_does_not_cure_contradiction', '合同存在无效或者可撤销的情形',
     '即使合同不存在无效或者可撤销的情形，任何已备案合同也一律无效。', False),
    ('optional_opinion_is_not_mandatory', '伤情有特殊需要的，可以参照辅助器具配制机构的意见',
     '伤情有特殊需要时，只有取得辅助器具配制机构意见支持，才可以采用不同于普通适用器具的合理费用标准。', False),
    ('multiple_disjoint_supports', '因劳动报酬、工伤医疗费、经济补偿或者赔偿金等发生的争议',
     '境内用人单位与劳动者因解除劳动合同或者劳动报酬发生的争议，适用该法。', True),
    ('last_item_condition_applied_to_all', '双方均无配偶的同居关系析产纠纷',
     '双方均无配偶的同居关系析产纠纷中，没有约定且协商不成时，只有共同出资购置财产、共同经营收益等无法区分的财产，才以各自出资比例为基础并综合共同生活、有无共同子女、贡献等因素分割。', False),
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
                                         '合成审核：只核对这一主张与给定原文是否一致。', model,
                                         validated_context='结论\n以下仅分析合同存在无效或者可撤销情形时，手续对效力判断的影响。\n\n'
                                         if name in {'inherited_condition','context_does_not_cure_contradiction'} else '')
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
    parser.add_argument('--allow-real-model', action='store_true', help='Explicitly enable paid model probes')
    args = parser.parse_args()
    if not args.allow_real_model:
        raise SystemExit('Use evaluate_offline for daily development; real probes require --allow-real-model')
    if args.output.exists():
        raise SystemExit('Choose a new output path')
    report = asyncio.run(evaluate())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['all_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
