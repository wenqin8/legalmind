"""Old failure mechanisms with explicit reviewed corrections, never new model scores."""

import hashlib
import json
from pathlib import Path

import pytest

from app.agents.evidence import Evidence, validate_citations
from app.agents.legal_references import reference_context
from app.agents.qa import checked_paragraph
from app.core.errors import ModelUnavailableError
from app.llm.fake import FakeLLMClient
from app.schemas.chat import SourceReference

ROOT = Path(__file__).resolve().parents[3]
CASES = json.loads((ROOT/'backend/data/evaluation/offline-v1/validation-cases.json').read_text(encoding='utf-8'))['cases']
LEGAL_UNITS = {'E-L-MF-04': 1, 'E-L-MF-05': 1, 'E-L-LD-03': 3, 'E-L-CD-02': 2,
               'E-L-LD-01': 2, 'E-L-LD-05': 2, 'E-L-TA-03': 4}


class ReviewedCorrection(FakeLLMClient):
    def __init__(self, case, *, repeat_bad=False):
        super().__init__()
        self.case = case
        self.repeat_bad = repeat_bad
        self.revisions = 0
        self.audits = []

    async def complete(self, messages):
        task = messages[0].content.split('\n')[0]
        payload = json.loads(messages[1].content)
        if task == 'TASK:REVISE':
            self.revisions += 1
            assert payload['validated_context'] == self.case['validated_context']
            assert 'reference_context' in payload
            return self.case['original_paragraph'] if self.repeat_bad else self.case['corrected_paragraph']
        assert task in {'TASK:GROUNDING', 'TASK:CONDITIONS'}
        self.audits.append(task)
        accepted = payload['paragraph'].strip() == self.case['corrected_paragraph'].strip()
        accepted &= payload['validated_context'] == self.case['validated_context']
        assert payload['evidence'][0]['text'] == self.case['source']['original_text']
        label = self.case['source']['citation_id']
        items = []
        for unit in payload['units']:
            if task == 'TASK:CONDITIONS':
                item = {'unit_id': unit['unit_id'], 'verdict': 'consistent' if accepted else 'unsupported'}
            else:
                legal = unit['unit_id'] < LEGAL_UNITS[self.case['scenario_id']]
                item = {'unit_id': unit['unit_id'], 'verdict': ('supported' if legal else 'neutral') if accepted else 'unsupported',
                        'supports': [{'citation_id': label, 'span_id': span['span_id']} for span in payload['evidence'][0]['spans']]
                                    if accepted and legal else []}
            items.append(item)
        return json.dumps({'items': items})


@pytest.mark.parametrize('case', CASES, ids=lambda case: case['scenario_id'])
@pytest.mark.anyio
async def test_archived_blocker_can_complete_with_validated_correction(case):
    path = ROOT/case['archive']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == case['archive_sha256']
    archive = json.loads(path.read_text(encoding='utf-8'))
    turn = next(s for s in archive['scenarios'] if s['id'] == case['scenario_id'])['turns'][case['turn']-1]
    assert turn['status'] == 424
    assert any(case['original_paragraph'] == (c['input'].get('paragraph') if isinstance(c['input'], dict) else None)
               or case['original_paragraph'] == c['output'] for c in turn['model_trace'])
    source = SourceReference.model_validate(case['source'])
    material = [Evidence(source, source.original_text)]
    model = ReviewedCorrection(case)
    result = await checked_paragraph(case['original_paragraph'], material, case['query'], model, case['validated_context'])
    assert model.revisions == 1
    assert 'TASK:CONDITIONS' in model.audits
    assert f'[{source.citation_id}]' in result
    validate_citations(result, material)
    # The untrusted original never replaces the reviewed correction.
    assert case['original_paragraph'].strip() != result.strip()


@pytest.mark.parametrize('case', CASES, ids=lambda case: case['scenario_id'])
@pytest.mark.anyio
async def test_unfixed_archived_failure_still_blocks_after_one_revision(case):
    source = SourceReference.model_validate(case['source'])
    model = ReviewedCorrection(case, repeat_bad=True)
    with pytest.raises(ModelUnavailableError):
        await checked_paragraph(case['original_paragraph'], [Evidence(source, source.original_text)],
                                case['query'], model, case['validated_context'])
    assert model.revisions == 1


def test_missing_cross_reference_is_not_confused_with_same_article_in_other_law():
    case = next(c for c in CASES if c['scenario_id'] == 'E-L-MF-04')
    source = SourceReference.model_validate(case['source'])
    wrong_law = source.model_copy(update={'title': '另一部法律', 'reference_number': '第一百五十七条', 'citation_id': 'S5'})
    refs = reference_context([Evidence(source, source.original_text), Evidence(wrong_law, '其他规定。')])
    reference = next(r for r in refs if r['reference'] == '民法典第一百五十七条')
    assert reference['status'] == 'not_provided' and reference['target_citation'] is None


def test_provided_same_regulation_dependency_is_resolved_to_server_label():
    case = next(c for c in CASES if c['scenario_id'] == 'E-L-CD-02')
    source = SourceReference.model_validate(case['source'])
    dependency = source.model_copy(update={'reference_number': '第三条', 'citation_id': 'S5'})
    refs = reference_context([Evidence(source, source.original_text), Evidence(dependency, '第三条 测试材料。')])
    reference = next(r for r in refs if r['reference'] == '本解释第三条')
    assert reference['status'] == 'provided' and reference['target_citation'] == 'S5'
