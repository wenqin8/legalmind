import json
from pathlib import Path

import pytest

from app.agents.evidence import Evidence
from app.agents.paragraph_revision import apply_sentence_repairs, repair_scope
from app.agents.qa import checked_paragraph
from app.core.errors import ModelUnavailableError
from app.schemas.chat import SourceReference


def test_only_failed_occurrence_is_replaced_and_all_other_text_is_unchanged():
    paragraph = '结论\n相同的句子。相同的句子。另一条已验证规则。\n\n'
    scope = repair_scope(paragraph, [{'unit_id': 1}])
    result = apply_sentence_repairs(paragraph, scope, json.dumps({'replacements': [{'unit_id': 1, 'text': '修订后的句子。'}]}))
    assert result == '结论\n相同的句子。修订后的句子。另一条已验证规则。\n\n'


@pytest.mark.parametrize('replacements', [
    [], [{'unit_id': 0, 'text': '越界修改。'}],
    [{'unit_id': 1, 'text': '修订。'}, {'unit_id': 1, 'text': '重复。'}],
    [{'unit_id': True, 'text': '错误编号。'}], [{'unit_id': 1, 'text': ''}],
    [{'unit_id': 1, 'text': '修订。新增法律主张。'}],
    [{'unit_id': 1, 'text': '风险\n新增段落。'}], [{'unit_id': 1, 'text': '修订。', 'extra': True}],
    [{'unit_id': 1, 'text': '风险\r新增段落。'}],
])
def test_repair_cannot_delete_expand_or_change_accepted_sentences(replacements):
    with pytest.raises(ModelUnavailableError):
        apply_sentence_repairs('结论\n已通过。未通过。', [{'unit_id': 1}], json.dumps({'replacements': replacements}))


@pytest.mark.parametrize('scenario', ['E-L-MF-06', 'E-L-CD-06'])
def test_recorded_single_sentence_with_semicolon_restores_conditions(scenario):
    root = Path(__file__).resolve().parents[3]
    report = json.loads((root / 'docs/acceptance/m4-real-development-20261001-run4.json').read_text(encoding='utf-8'))
    turn = next(s for s in report['scenarios'] if s['id'] == scenario)['turns'][0]
    revision = next(c for c in turn['model_trace'] if c['task'] == 'TASK:REVISE')
    paragraph, scope = revision['input']['paragraph'], revision['input']['repair_units']
    assert turn['status'] == 424 and len(scope) == 1
    replacement = json.loads(revision['output'])['replacements'][0]['text']
    assert '；' in replacement and replacement.count('。') == 1
    result = apply_sentence_repairs(paragraph, scope, revision['output'])
    assert result == paragraph.replace(scope[0]['text'], replacement, 1)


def test_recorded_repair_with_citation_after_sentence_is_one_sentence():
    root = Path(__file__).resolve().parents[3]
    report = json.loads((root / 'docs/acceptance/m4-real-development-20261001-run5.json').read_text(encoding='utf-8'))
    turn = next(s for s in report['scenarios'] if s['id'] == 'E-L-CD-03')['turns'][0]
    revision = next(c for c in turn['model_trace'] if c['task'] == 'TASK:REVISE')
    scope = revision['input']['repair_units']
    replacement = json.loads(revision['output'])['replacements'][0]['text']
    assert turn['status'] == 424 and replacement.endswith('。[S1]')
    assert apply_sentence_repairs(revision['input']['paragraph'], scope, revision['output']) == (
        revision['input']['paragraph'].replace(scope[0]['text'], replacement, 1))


@pytest.mark.anyio
@pytest.mark.parametrize('repaired_supported', [True, False])
async def test_semicolon_repair_reaudits_all_clauses_and_can_still_fail(repaired_supported):
    root = Path(__file__).resolve().parents[3]
    report = json.loads((root / 'docs/acceptance/m4-real-development-20261001-run4.json').read_text(encoding='utf-8'))
    trace = next(s for s in report['scenarios'] if s['id'] == 'E-L-MF-06')['turns'][0]['model_trace']
    revision = next(c for c in trace if c['task'] == 'TASK:REVISE')
    grounding = [c for c in trace if c['task'] == 'TASK:GROUNDING'][-1]
    condition = [c for c in trace if c['task'] == 'TASK:CONDITIONS'][-1]
    selection = next(c for c in trace if c['task'] == 'TASK:APPLICABILITY')
    selected = set(json.loads(selection['output'])['source_ids'])
    evidence = [Evidence(SourceReference.model_validate(c['source']), c['source']['original_text'])
                for c in selection['input']['candidates'] if c['source_id'] in selected]
    calls = []
    class RecordedReview:
        async def complete(self, messages):
            task = messages[0].content.split('\n')[0]
            data = json.loads(messages[1].content)
            calls.append(task)
            if task == 'TASK:REVISE':
                return revision['output']
            if calls.count('TASK:REVISE') == 0:
                return grounding['output'] if task == 'TASK:GROUNDING' else condition['output']
            assert len(data['units']) == 3
            if task == 'TASK:CONDITIONS':
                return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'consistent'} for u in data['units']]})
            return json.dumps({'items': [
                {'unit_id': 0, 'verdict': 'supported', 'supports': [{'citation_id': 'S1', 'span_id': 0}]},
                {'unit_id': 1, 'verdict': 'supported' if repaired_supported else 'unsupported',
                 'supports': [{'citation_id': 'S1', 'span_id': 2}], 'explanation': '复核全部修订分句'},
                {'unit_id': 2, 'verdict': 'neutral'}]})
    call = checked_paragraph(revision['input']['paragraph'], evidence, revision['input']['query'],
                             RecordedReview(), revision['input']['validated_context'])
    if repaired_supported:
        assert '；' in await call
        assert calls[-2:] == ['TASK:GROUNDING', 'TASK:CONDITIONS']
    else:
        with pytest.raises(ModelUnavailableError):
            await call
        assert calls[-2:] == ['TASK:GROUNDING', 'TASK:CONDITIONS']
    assert calls.count('TASK:REVISE') == 1


@pytest.mark.anyio
async def test_recorded_partial_rejection_repairs_only_failed_sentence_and_is_reaudited():
    root = Path(__file__).resolve().parents[3]
    report = json.loads((root / 'docs/acceptance/rag-v2-development-answers-run14.json').read_text(encoding='utf-8'))
    turn = next(s for s in report['scenarios'] if s['id'] == 'E-L-LD-01')['turns'][0]
    assert turn['status'] == 424
    trace = turn['model_trace']
    check = next(c for c in trace if c['task'] == 'TASK:CONDITIONS')
    paragraph = check['input']['paragraph']
    select = next(c for c in trace if c['task'] == 'TASK:APPLICABILITY')
    selected = set(json.loads(select['output'])['source_ids'])
    evidence = [Evidence(SourceReference.model_validate(c['source']), c['source']['original_text'])
                for c in select['input']['candidates'] if c['source_id'] in selected]
    correction = '用人单位未依法缴纳社会保险费，劳动者根据未依法缴纳社会保险费这一法定事由请求解除劳动合同并由用人单位支付经济补偿的，人民法院依法予以支持[S1][S4][S5]。'
    calls = []
    class RecordedReview:
        async def complete(self, messages):
            task = messages[0].content.split('\n')[0]
            data = json.loads(messages[1].content)
            calls.append(task)
            if task == 'TASK:REVISE':
                assert data['repair_units'] == [{'unit_id': 1, 'text': check['input']['units'][1]['text']}]
                return json.dumps({'replacements': [{'unit_id': 1, 'text': correction}]})
            if task == 'TASK:CONDITIONS':
                if calls.count(task) == 1:
                    return check['output']
                assert correction in data['paragraph'] and '返还' not in data['paragraph']
                return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'consistent'} for u in data['units']]})
            assert task == 'TASK:GROUNDING'
            return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'supported',
                'supports': [{'citation_id': 'S1', 'span_id': u['unit_id']}]} for u in data['units']]})
    result = await checked_paragraph(paragraph, evidence, check['input']['query'], RecordedReview())
    assert '返还' not in result
    assert calls == ['TASK:GROUNDING', 'TASK:CONDITIONS', 'TASK:REVISE', 'TASK:GROUNDING', 'TASK:CONDITIONS']
