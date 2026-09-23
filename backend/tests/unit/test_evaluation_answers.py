from uuid import uuid4
from datetime import date
import pytest

from app.evaluation.answers import check_turn, observed_behavior, date_bounds


def fixture_data():
    uid=str(uuid4());turn=str(uuid4())
    source={'source_type':'legal_provision','source_id':uid,'citation_id':'S1','title':'测试法',
        'reference_number':'第一条','source_url':'https://example.gov.cn/law','version':'2020版本',
        'original_text':'第一条 应当履行义务。','effective_from':'2021-01-01','effective_until':None,
        'verified_at':'2026-09-18','status_as_of':'2026-03-12'}
    data={'response':'结论\n有条件参考[S1]。','sources':[source],'missing_fields':[],
          'task':{'mode':'event','phase':'completed','fields':{'event_date':{'value':'2025年6月1日','quote':'2025年6月1日',
                    'source_turn_id':turn,'source':'message'}}}}
    known={uid:{'record_id':'law-1',**source}}
    return data,known,{turn:'合成事件发生于2025年6月1日。'}


def test_answer_checks_detect_source_tampering_unknown_labels_and_ungrounded_fields():
    data,known,provenance=fixture_data()
    result=check_turn(data,{'expected':'answer'},known,[],{'law-1':3},provenance)
    assert result['structural_passed']
    data['sources'][0]['title']='伪造法名'
    data['response']+='[S9]'
    data['task']['fields']['event_date']['value']='2035年'
    result=check_turn(data,{'expected':'answer'},known,[],{'law-1':3},provenance)
    assert not result['checks']['source_integrity']
    assert not result['checks']['known_citations']
    assert not result['checks']['field_provenance']


def test_answer_checks_separate_quotes_intervals_and_behavior():
    data,known,provenance=fixture_data()
    data['response']='规定为“必须胜诉”[S1] https://fake.example'
    data['task']['fields']['event_date']['value']='1990年'
    result=check_turn(data,{'expected':'insufficient'},known,[],{},provenance)
    assert not result['checks']['verbatim_quotes'] and not result['checks']['no_model_urls']
    assert not result['checks']['version_interval'] and not result['checks']['expected_behavior']
    data['task']['phase']='collecting';data['missing_fields']=['event_date']
    assert observed_behavior(data)=='clarify'
    data['task']['phase']='conflict'
    assert observed_behavior(data)=='conflict'


def test_conflict_must_preserve_old_value_and_confirmed_revision_must_apply():
    data,known,provenance=fixture_data()
    data['task']['phase']='conflict'
    expected={'expected':'conflict','preserve_field':'event_date','preserve_contains':'6月1日'}
    assert check_turn(data,expected,known,[],{},provenance)['checks']['conflict_preserved']
    expected['preserve_contains']='7月1日'
    assert not check_turn(data,expected,known,[],{},provenance)['checks']['conflict_preserved']


def test_filtering_metrics_expose_lost_relevant_candidate():
    data,known,provenance=fixture_data()
    uid=next(iter(known))
    trace=[{'task':'TASK:APPLICABILITY','input':{'candidates':[{'source_id':uid}]}},
           {'task':'TASK:QA','input':{'evidence':[]}}]
    result=check_turn(data,{'expected':'answer'},known,trace,{'law-1':3},provenance)
    assert result['candidate_metrics']['recall']==1
    assert result['selected_metrics']['recall']==0


def test_selection_preserves_model_input_order_not_catalog_order():
    data,known,provenance=fixture_data()
    uid=next(iter(known))
    second=str(uuid4())
    known[second]={**known[uid],'record_id':'law-2','original_text':'第二条 另一规则。'}
    trace=[{'task':'TASK:APPLICABILITY','input':{'candidates':[
        {'source_id':second,'source':{'citation_id':'S1'}},{'source_id':uid,'source':{'citation_id':'S2'}}]}},
        {'task':'TASK:QA','input':{'evidence':[
            {'citation_id':'S1','text':known[second]['original_text']},{'citation_id':'S2','text':known[uid]['original_text']}]}}]
    result=check_turn(data,{'expected':'answer'},known,trace,{'law-1':3},provenance)
    assert result['selected_ids']==['law-2','law-1']
    assert result['selected_metrics']['reciprocal_rank']==.5


@pytest.mark.parametrize('text,expected',[
    ('2026-06-01',(date(2026,6,1),date(2026,6,1))),
    ('2022年4月至2022年6月',(date(2022,4,1),date(2022,6,30))),
    ('2025年',(date(2025,1,1),date(2025,12,31))),
    ('2025年2月30日',(None,None)),
    ('去年',(None,None)),
])
def test_answer_version_check_covers_full_dates_and_ranges(text,expected):
    assert date_bounds(text)==expected


def test_failed_generation_retains_retrieval_measurements(monkeypatch):
    from scripts import review_rag_answers as reviewer
    data,known,provenance=fixture_data();uid=next(iter(known))
    from types import SimpleNamespace
    monkeypatch.setattr(reviewer,'load_queries',lambda:[SimpleNamespace(id='q',relevance={'law-1':SimpleNamespace(grade=3)})])
    monkeypatch.setattr(reviewer,'known_sources',lambda:known)
    raw={'started_at':'test','complete':True,'scenarios':[{'id':'s','query_id':'q','domain':'labor_dispute','split':'development',
        'turns':[{'status':424,'expected':{'expected':'answer'},'model_trace':[
            {'task':'TASK:APPLICABILITY','input':{'candidates':[{'source_id':uid,'source':{'citation_id':'S1'}}]}},
            {'task':'TASK:QA','input':{'evidence':[{'citation_id':'S1','text':known[uid]['original_text']}]}}]}]}]}
    result=reviewer.review(raw)
    assert result['metrics']['candidate_recall_on_expected_answers']['value']==1
    assert result['metrics']['selected_recall_on_expected_answers']['value']==1
    assert result['metrics']['returned_recall_on_expected_answers']['value']==0
