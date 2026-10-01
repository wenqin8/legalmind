"""Observed MF04 defects and counterexamples, without a model provider."""

import json

import pytest

from app.agents.claim_rules import deterministic_rejections
from app.agents.evidence import Evidence, validate_citations
from app.agents.grounding import sentence_units
from app.agents.legal_references import normalize_cross_references
from app.evaluation.recorded_audits import load_cases
from app.rag.catalog_profiles import profile_entries
from app.rag.legal_catalog import import_catalog, retrieve_provisions


def observed_case():
    return next(case for case in load_cases()[1]
                if case['id'] == 'm4-real-development-20261001-run11:E-L-MF-04:1:6')


def test_exact_reference_complements_available_exception_without_inventing_missing_law(app):
    import_catalog(app.state.database, profile_entries('eval-rag-v2-209'))
    rows = retrieve_provisions(app.state.database, observed_case()['payload']['query'],
                               'marriage_family', event_date=None, general=True)
    keys = {row.record_id for row, _ in rows}
    assert len(rows) <= 5
    assert {'marriage_ii-2025-01-15-7', 'civil_code-2020-05-28-1062',
            'civil_code-2020-05-28-1063'} <= keys
    # These full texts are absent from the reviewed catalog, rather than lost by ranking.
    assert not any(p.record.article_number in {'第一百五十七条', '第一千零六十六条', '第一千零九十二条'}
                   for p in profile_entries('eval-rag-v2-209'))


def test_multiple_missing_cross_references_keep_distinct_identity_and_unknown_stays_visible():
    evidence = observed_case()['evidence']
    text = '依民法典第一百五十七条处理；依民法典第一千零六十六条请求；依第九千九百条处理。'
    normalized = normalize_cross_references(text, evidence)
    clauses = normalized.split('；')
    assert clauses[0].removeprefix('依').removesuffix('处理') != clauses[1].removeprefix('依').removesuffix('请求')
    assert '配套引用1' in clauses[0] and '配套引用2' in clauses[1]
    assert '被引用全文本轮未提供' in clauses[0]
    assert '第九千九百条' in normalized


@pytest.mark.parametrize('candidate', [
    '婚姻关系存续期间所得的相关财产为夫妻共同财产，夫妻对共同财产有平等的处理权[S4]。',
    '婚姻关系存续期间所得的财产均为夫妻共同财产[S4]。',
    '夫妻共同财产包括婚姻关系存续期间所有所得的财产[S4]。',
])
def test_observed_overbroad_property_scope_is_rejected_before_model_agreement(candidate):
    assert deterministic_rejections(sentence_units(candidate), observed_case()['evidence'])


@pytest.mark.parametrize('candidate', [
    '上述规则以夫妻共同财产为前提[S2]。',
    '夫妻对共同财产有平等的处理权[S4]。',
    '婚姻关系存续期间所得的财产并非全部都是夫妻共同财产；本次不判断具体财产归属。',
    '不能认为婚姻关系存续期间所得的财产均为夫妻共同财产。',
    '共同财产不是婚姻关系存续期间所有所得的财产。',
])
def test_property_premise_and_nonconclusion_do_not_trigger_overbroad_guard(candidate):
    assert not deterministic_rejections(sentence_units(candidate), observed_case()['evidence'])


def test_disclaimer_does_not_rescue_an_overbroad_property_claim():
    candidate = '婚姻关系存续期间所得的相关财产为夫妻共同财产，但不是说已核实个案财产归属[S4]。'
    assert deterministic_rejections(sentence_units(candidate), observed_case()['evidence'])


@pytest.mark.anyio
async def test_same_source_direct_and_context_spans_are_not_merged_into_new_requests(app):
    from app.agents.legal_evidence import legal_evidence
    from app.llm.fake import FakeLLMClient
    from app.schemas.tasks import TaskState

    import_catalog(app.state.database, profile_entries('eval-rag-v2-209'))

    class Selection(FakeLLMClient):
        async def complete(self, messages):
            candidates = json.loads(messages[1].content)['candidates']
            entry = next(e for e in candidates if e['source']['reference_number'] == '第七条')
            key = entry['source_id']
            return json.dumps({'source_ids': [key], 'assessment': 'general',
                               'direct_support': {key: [0]}, 'supporting_support': {key: [0, 1]}})

    result = await legal_evidence(app.state.database, observed_case()['payload']['query'],
                                 TaskState(kind='qa', mode='general', domain='marriage_family'), Selection())
    assert result.status == 'answer'
    selected = result.evidence[0]
    assert selected.support_span_ids == (0, 1)
    assert selected.context_span_ids == (1,)
    assert selected.text == selected.source.original_text


def scoped_evidence():
    first, second = observed_case()['evidence']
    return [Evidence(first.source, first.text, 'direct', (0, 1), (1,)),
            Evidence(second.source, second.text, 'supporting', (6,))]


@pytest.mark.anyio
async def test_generation_and_both_audits_keep_scope_and_full_condition_context():
    from app.agents.qa import generate_qa, FACT_RISK, FACT_NEXT
    from app.evaluation.offline_guard import OfflineGuard
    from tests.agent_helpers import AgentLLM

    rows = scoped_evidence()
    class Model(AgentLLM):
        async def stream(self, messages):
            payload = json.loads(messages[1].content)
            direct = payload['evidence'][0]
            assert direct['selected_spans'][0]['purpose'] == 'answer'
            assert direct['selected_spans'][1]['purpose'] == 'context'
            assert direct['text'] == rows[0].text
            async for delta in super().stream(messages):
                yield delta

        async def complete(self, messages):
            if messages[0].content.startswith(('TASK:GROUNDING', 'TASK:CONDITIONS')):
                payload = json.loads(messages[1].content)
                scope = payload['selection_scope'][0]
                assert scope['answer_span_ids'] == [0] and scope['context_span_ids'] == [1]
                assert payload['evidence'][0]['text'] == rows[0].source.original_text
            return await super().complete(messages)

    model = Model()
    model.response = ('结论\n共同财产处置应核对忠实义务相关目的及主张无效的前提[S2]。'
                      '夫妻对共同财产有平等的处理权[S4]。\n\n' + FACT_RISK + '\n\n' + FACT_NEXT)
    with OfflineGuard() as guard:
        parts = [part async for part in generate_qa(observed_case()['payload']['query'], [], rows, model)]
    assert not guard.attempts
    assert len([c for c in model.requests if c[0].content.startswith('TASK:CONDITIONS')]) == 1
    assert '参考材料' in parts[-1]
    # Scripted outputs exercise scope transport, not the effectiveness of a new prompt.


@pytest.mark.anyio
async def test_one_scoped_repair_can_remove_an_unasked_claim_without_losing_prior_rule():
    from app.agents.qa import checked_paragraph
    from app.evaluation.offline_guard import OfflineGuard
    from app.llm.fake import FakeLLMClient

    paragraph = ('夫妻对共同财产有平等的处理权[S4]。'
                 '另一方请求离婚财产分割时可以要求对该方少分或者不分[S2]。')
    repaired = '本次不展开婚内或离婚财产分割。'
    class Model(FakeLLMClient):
        def __init__(self):
            super().__init__()
            self.tasks = []

        async def complete(self, messages):
            task = messages[0].content.splitlines()[0]
            self.tasks.append(task)
            payload = json.loads(messages[1].content)
            assert payload['selection_scope'][0]['context_span_ids'] == [1]
            if task == 'TASK:REVISE':
                assert [u['unit_id'] for u in payload['repair_units']] == [1]
                return json.dumps({'replacements': [{'unit_id': 1, 'text': repaired}]})
            failure = repaired not in payload['paragraph']
            if task == 'TASK:CONDITIONS':
                return json.dumps({'items': [{'unit_id': 0, 'verdict': 'consistent'},
                    {'unit_id': 1, 'verdict': 'unsupported' if failure else 'consistent',
                     'explanation': '配套片段扩展了用户未问的独立财产分割请求。' if failure else ''}]})
            return json.dumps({'items': [{'unit_id': 0, 'verdict': 'supported',
                'supports': [{'citation_id': 'S4', 'span_id': 6}]},
                {'unit_id': 1, 'verdict': 'supported' if failure else 'neutral',
                 'supports': [{'citation_id': 'S2', 'span_id': 1}] if failure else []}]})

    model = Model()
    with OfflineGuard() as guard:
        result = await checked_paragraph(paragraph, scoped_evidence(), observed_case()['payload']['query'], model)
    assert not guard.attempts
    assert '夫妻对共同财产有平等的处理权' in result and repaired in result
    assert '可以要求' not in result
    assert model.tasks == ['TASK:GROUNDING', 'TASK:CONDITIONS', 'TASK:REVISE',
                           'TASK:GROUNDING', 'TASK:CONDITIONS']


def test_reference_labels_are_idempotent_and_still_pass_source_validation():
    rows = observed_case()['evidence']
    result = normalize_cross_references('依民法典第一百五十七条处理[S2]。', rows)
    assert normalize_cross_references(result, rows) == result
    validate_citations(result, rows)


def test_same_status_bare_references_to_different_statutes_remain_ambiguous():
    source = observed_case()['evidence'][0].source
    first = Evidence(source.model_copy(update={'title': '中华人民共和国民法典'}), '本法第八条规定。')
    second = Evidence(source.model_copy(update={'title': '中华人民共和国劳动合同法', 'citation_id': 'S4'}),
                      '劳动合同法第八条规定。')
    rows = [first, second]
    assert normalize_cross_references('依第八条处理。', rows) == '依第八条处理。'
    assert '配套引用2' in normalize_cross_references('依劳动合同法第八条处理。', rows)


def test_repeated_explicit_reference_to_same_statute_has_one_identity():
    rows = observed_case()['evidence']
    repeated = Evidence(rows[0].source.model_copy(update={'citation_id': 'S1'}), rows[0].text)
    result = normalize_cross_references('依民法典第一百五十七条处理。', [rows[0], repeated])
    assert '第一百五十七条' not in result and '配套引用1' in result


@pytest.mark.parametrize('excluded', ['future', 'wrong_domain', 'unknown'])
def test_reference_expansion_obeys_existing_catalog_filters(app, excluded):
    entries = profile_entries('eval-rag-v2-209')
    target = next(e for e in entries if e.record.record_id == 'civil_code-2020-05-28-1063')
    data = target.model_dump(mode='json')
    if excluded == 'future':
        data['verification']['effective_from'] = data['record']['effective_at'] = '2099-01-01'
    elif excluded == 'wrong_domain':
        data['verification']['domains'] = ['contract_dispute']
    else:
        data['record']['legal_status'] = 'unknown'
    from app.rag.legal_catalog import CatalogRecord
    modified = CatalogRecord.model_validate(data)
    import_catalog(app.state.database, [modified if e == target else e for e in entries])
    rows = retrieve_provisions(app.state.database, observed_case()['payload']['query'],
                               'marriage_family', event_date=None, general=True)
    assert len(rows) <= 5
    assert target.record.record_id not in {row.record_id for row, _ in rows}
