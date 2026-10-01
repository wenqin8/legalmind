"""Run21 coverage failures must get one repair and full revalidation."""
import json
from pathlib import Path
import pytest
from app.agents.evidence import Evidence
from app.agents.qa import complete_coverage
from app.schemas.chat import SourceReference
from app.core.errors import ModelUnavailableError


@pytest.mark.anyio
@pytest.mark.parametrize('scenario', ['E-L-MF-02', 'E-L-CD-02'])
@pytest.mark.parametrize('repair_valid', [True, False])
async def test_recorded_coverage_failure_is_repaired_once_and_reaudited(scenario, repair_valid):
    report = json.loads((Path(__file__).resolve().parents[3] / 'docs/acceptance/rag-v2-development-answers-run21.json').read_text(encoding='utf-8'))
    trace = next(s for s in report['scenarios'] if s['id'] == scenario)['turns'][0]['model_trace']
    coverage = next(c for c in trace if c['task'] == 'TASK:COVERAGE')
    selection = next(c for c in trace if c['task'] == 'TASK:APPLICABILITY')
    selected = set(json.loads(selection['output'])['source_ids'])
    evidence = [Evidence(SourceReference.model_validate(c['source']), c['source']['original_text'], 'supporting', (0,)) for c in selection['input']['candidates'] if c['source_id'] in selected]
    calls = []
    class Model:
        async def complete(self, messages):
            task = messages[0].content.splitlines()[0]; calls.append(task)
            data = json.loads(messages[1].content)
            if task == 'TASK:COVERAGE': return coverage['output']
            if task == 'TASK:REVISE':
                replacement = '规则说明[S2]。' if repair_valid else '没有对应来源[S9]。'
                if data['repair_units']:
                    return json.dumps({'replacements': [{'unit_id': u['unit_id'], 'text': replacement} for u in data['repair_units']]})
                return '补充说明\n' + replacement
            verdict = 'supported' if task == 'TASK:GROUNDING' else 'consistent'
            items = [{'unit_id': u['unit_id'], 'verdict': verdict} for u in data['units']]
            if task == 'TASK:GROUNDING':
                for item in items:
                    item['supports'] = [{'citation_id':'S2','span_id':0}]
                if calls.count('TASK:REVISE') == 0:
                    items[-1].update(verdict='unsupported', supports=[], explanation='补充说明中存在原文不支持的推论')
            return json.dumps({'items': items})
    call = complete_coverage('问题', evidence, '结论\n已经验证的前文[S1]。', Model())
    if repair_valid:
        result = await call
        assert '[S2]' in result
        assert calls[-2:] == ['TASK:GROUNDING','TASK:CONDITIONS']
    else:
        with pytest.raises(ModelUnavailableError): await call
    assert calls.count('TASK:COVERAGE') == 1
    assert calls.count('TASK:REVISE') == 1
