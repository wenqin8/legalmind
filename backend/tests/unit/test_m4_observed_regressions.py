"""Replay observed M4 failures; these records are development data now."""
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.agents.claim_rules import deterministic_rejections
from app.agents.evidence import Evidence, validate_citations
from app.agents.grounding import sentence_units
from app.agents.intent import classify_intent
from app.agents.legal_references import normalize_cross_references
from app.agents.tasks import advance_task
from app.llm.fake import FakeLLMClient
from app.schemas.chat import ChatRequest, SourceReference
from tests.unit.test_tasks import ExtractLLM

ROOT = Path(__file__).resolve().parents[3]


def turn(suffix, filename='m4-once-v6-first-observation.json', index=0):
    report = json.loads((ROOT / 'docs/acceptance' / filename).read_text(encoding='utf-8'))
    return next(s for s in report['scenarios'] if s['id'].endswith(suffix))['turns'][index]


def selected_evidence(record):
    selection = next(c for c in record['model_trace'] if c['task'] == 'TASK:APPLICABILITY')
    ids = json.loads(selection['output'])['source_ids']
    return [Evidence(SourceReference.model_validate(c['source']), c['source']['original_text'])
            for c in selection['input']['candidates'] if c['source_id'] in ids]


@pytest.mark.anyio
@pytest.mark.parametrize('domain', ['traffic_accident', 'contract_dispute', 'marriage_family'])
async def test_regional_policy_lookup_cannot_become_case_search(domain):
    record = turn(domain + '-06')
    output = next(c['output'] for c in record['model_trace'] if c['task'] == 'TASK:INTENT')
    decision = await classify_intent(ChatRequest(message=record['expected']['message']), FakeLLMClient(output))
    assert decision.intent == 'qa'


@pytest.mark.anyio
async def test_soft_request_for_similar_cases_remains_case_search():
    decision = await classify_intent(ChatRequest(message='有没有类似的判例供参考？'),
                                     FakeLLMClient('{"intent":"search","confidence":0.95}'))
    assert decision.intent == 'search'


@pytest.mark.anyio
async def test_statutory_effective_date_does_not_require_event_facts():
    record = turn('marriage_family-03')
    task, _ = await advance_task(ChatRequest(message=record['expected']['message']), None,
        kind='qa', turn_id=uuid4(), llm=ExtractLLM(domain='marriage_family', general=True))
    assert task.mode == 'general' and task.phase == 'completed' and not task.missing_fields


@pytest.mark.anyio
async def test_date_of_users_event_still_requires_event_facts():
    task, _ = await advance_task(ChatRequest(message='只问日期：我这次离婚诉讼哪天能开始？'), None,
        kind='qa', turn_id=uuid4(), llm=ExtractLLM(domain='marriage_family', general=True))
    assert task.mode == 'event' and task.phase == 'collecting'


def test_original_backed_bare_statutory_references_are_normalized_and_unknown_stays_rejected():
    record = turn('contract_dispute-02')
    evidence = selected_evidence(record)
    paragraph = next(c['output'] for c in record['model_trace'] if c['task'] == 'TASK:QA')
    normalized = normalize_cross_references(paragraph, evidence)
    assert '第一编第六章第三节' not in normalized and '第五百零六条' not in normalized
    assert '不合理免除' in normalized and '本次未提供' in normalized
    validate_citations(normalized, evidence)
    from app.core.errors import ModelUnavailableError
    with pytest.raises(ModelUnavailableError):
        validate_citations(normalize_cross_references('依第九千九百条无效[S1]。', evidence), evidence)


def test_provided_rule_cannot_be_described_as_missing_material():
    record = turn('E-L-LD-05', 'm4-real-development-20261001-run6.json', index=1)
    evidence = selected_evidence(record)
    output = record['response']['response']
    assert deterministic_rejections(sentence_units(output), evidence)
    assert not deterministic_rejections(['本次不展开不能继续履行的具体认定。'], evidence)
    assert not deterministic_rejections(['本次资料未提供地方最低工资标准。'], evidence)


def test_life_needs_exception_is_in_first_repair_feedback():
    record = turn('contract_dispute-01')
    evidence = selected_evidence(record)
    paragraph = next(c['output'] for c in record['model_trace'] if c['task'] == 'TASK:QA')
    rejected = deterministic_rejections(sentence_units(paragraph), evidence)
    assert rejected and '生活需要' in rejected[0]['explanation']
    complete = paragraph + '但当事人确因生活需要交易，未给社会公共秩序造成重大影响，且不影响国家安全，也不违背善良风俗的，不应认定合同无效[S1]。'
    assert not deterministic_rejections(sentence_units(complete), evidence)


@pytest.mark.anyio
async def test_cross_domain_question_keeps_versions_and_finds_existing_direct_rule(app):
    from app.agents.legal_evidence import legal_evidence
    from app.evaluation.dataset import catalog_entries
    from app.rag.legal_catalog import import_catalog
    from app.schemas.tasks import TaskState
    import_catalog(app.state.database, catalog_entries())
    record = turn('traffic_accident-03')
    class SelectDirect(FakeLLMClient):
        async def complete(self, messages):
            candidates = json.loads(messages[1].content)['candidates']
            assert len(candidates) <= 5
            item = next(c for c in candidates if c['source']['reference_number'] == '第三条'
                        and '工伤保险' in c['source']['original_text'])
            key = item['source_id']
            return json.dumps({'source_ids': [key], 'assessment': 'general', 'direct_support': {key: [0]}})
    result = await legal_evidence(app.state.database, record['expected']['message'],
                                 TaskState(kind='qa', domain='labor_dispute', mode='general'), SelectDirect())
    assert result.status == 'answer'
    assert result.evidence[0].source.version and result.evidence[0].source.verified_at


@pytest.mark.anyio
async def test_one_repair_receives_both_partial_audit_failures():
    from app.agents.grounding import validate_grounding, GroundingViolation
    record = turn('contract_dispute-02', 'm4-observed-v6-development-20261001-run2.json')
    evidence = selected_evidence(record)
    paragraph = next(c['output'] for c in record['model_trace'] if c['task'] == 'TASK:QA')
    calls = [c for c in record['model_trace'] if c['task'] in ('TASK:GROUNDING', 'TASK:CONDITIONS')]
    # Use recorded first support rejection and final condition rejection to
    # verify orchestration, without asserting that these legal verdicts are right.
    outputs = {'TASK:GROUNDING': calls[0]['output'], 'TASK:CONDITIONS': calls[-1]['output']}
    class PartialAudits(FakeLLMClient):
        async def complete(self, messages):
            return outputs[messages[0].content.split('\n')[0]]
    with pytest.raises(GroundingViolation) as failure:
        await validate_grounding(paragraph, evidence, '格式条款', PartialAudits())
    assert {f['unit_id'] for f in failure.value.feedback} == {0, 1}


def test_actual_cross_reference_gap_is_displayed_without_invented_effects():
    from app.agents.limitations import missing_cross_reference_notice
    record = turn('E-L-MF-04', 'm4-real-development-20261001-run8.json')
    evidence = selected_evidence(record)
    answer = record['response']['response'].split('参考材料')[0]
    notice = missing_cross_reference_notice(answer, evidence)
    assert notice and '未提供' in notice and '本次不作判断' in notice
    assert '返还' not in notice and '第一百五十七条' not in notice
    validate_citations(notice, evidence)
    supplied = turn('E-L-CD-02', 'm4-real-development-20261001-run8.json')
    # S1's referenced provision is present; S2 itself has another missing
    # cross-reference. Only the latter receives a material-gap notice.
    supplied_notice = missing_cross_reference_notice(supplied['response']['response'], selected_evidence(supplied))
    assert '[S1]' not in supplied_notice and '[S2]' in supplied_notice
    assert missing_cross_reference_notice('本次只介绍其他分支[S2]。', evidence) == ''


@pytest.mark.parametrize('scenario', ['E-L-MF-03', 'E-L-CD-05'])
def test_newly_observed_restriction_omissions_are_rejected(scenario):
    record = turn(scenario, 'm4-real-development-20261001-run9.json', index=1 if scenario.endswith('05') else 0)
    paragraph = record['response']['response'].split('风险\n')[0]
    assert deterministic_rejections(sentence_units(paragraph), selected_evidence(record))


def test_correct_gift_and_invalidity_conditions_stay_allowed():
    gift = selected_evidence(turn('E-L-MF-03', 'm4-real-development-20261001-run9.json'))
    assert not deterministic_rejections(['一方父母全额出资购房，赠与合同没有约定或者约定不明确的，离婚分割时可以按原文因素处理[S1]。'], gift)
    invalid = selected_evidence(turn('E-L-CD-05', 'm4-real-development-20261001-run9.json', index=1))
    assert not deterministic_rejections(['合同存在无效或者可撤销的情形，当事人仅以已经备案为由主张有效的，不予支持[S1]。'], invalid)


def test_normalized_reference_distinguishes_provided_rule_from_missing_fulltext():
    missing = selected_evidence(turn('E-L-MF-04', 'm4-real-development-20261001-run9.json'))
    assert '被引用全文本轮未提供' in normalize_cross_references('依民法典第一百五十七条处理[S2]。', missing)
    supplied = selected_evidence(turn('E-L-CD-02', 'm4-real-development-20261001-run9.json'))
    assert '本轮已提供的配套条款' in normalize_cross_references('本解释第三条第一款规定的条件[S1]。', supplied)
