"""Independent structural answer checks; semantic legal review remains separate."""

import re
from datetime import date

from app.evaluation.metrics import ranking_metrics


def date_bounds(value: str):
    """Parse all explicit date endpoints, without calling the production date filter."""
    from calendar import monthrange
    pattern=r'(?<!\d)(\d{4})(?:年|[-/])(?:(\d{1,2})(?:月|[-/])?(?:(\d{1,2})日?)?)?'
    endpoints=[]
    try:
        for year,month,day in re.findall(pattern,value):
            y=int(year);m=int(month) if month else None;d=int(day) if day else None
            endpoints += [date(y,m or 1,d or 1), date(y,m or 12,d or (monthrange(y,m)[1] if m else 31))]
    except ValueError:return None,None
    return (min(endpoints),max(endpoints)) if endpoints else (None,None)


def observed_behavior(data: dict) -> str:
    task=data.get('task') or {}
    if task.get('phase') in ('conflict','cancelled'):
        return task['phase']
    if data.get('missing_fields') or task.get('phase')=='collecting':
        return 'clarify'
    if any(s['source_type']=='legal_provision' for s in data.get('sources',[])):
        return 'answer'
    if re.search('依据不足|资料不足|不能.*法律依据|无法.*结论|不能.*具体法律',data.get('response','')):
        return 'insufficient'
    return 'other'


def check_turn(data: dict, expected: dict, known_sources: dict, trace: list[dict], gold: dict[str,int], provenance: dict[str,str]) -> dict:
    behavior=observed_behavior(data)
    checks={'expected_behavior':behavior==expected['expected'], 'source_integrity':True,
            'known_citations':True,'verbatim_quotes':True,'no_model_urls':True,'version_interval':True,
            'field_provenance':True,'expected_missing':True,'conflict_preserved':True,'confirmed_field':True}
    returned=[]; candidate_ids=[]; selected_ids=[]; candidate_by_label={}
    for source in data.get('sources',[]):
        if source['source_type']!='legal_provision': continue
        record=known_sources.get(source['source_id'])
        if record is None:
            checks['source_integrity']=False; continue
        returned.append(record['record_id'])
        checks['source_integrity'] &= all(source.get(key)==record.get(key) for key in (
            'title','reference_number','source_url','version','original_text','effective_from','effective_until','verified_at','status_as_of'))
    labels={source['citation_id'] for source in data.get('sources',[])}
    # Exclude the server's verbatim appendix, which may contain references within statute text.
    generated=data.get('response','').split('\n\n参考材料\n',1)[0]
    checks['known_citations']=all(label in labels for label in re.findall(r'\[([^\]\n]+)\]',generated))
    checks['relevant_answer_source']=bool(set(returned)&set(gold)) if expected['expected']=='answer' else True
    source_by_label={s['citation_id']:s for s in data.get('sources',[])}
    for match in re.finditer(r'[“"]([^”"]+)[”"]\s*\[(S\d+)\]',generated):
        original=source_by_label.get(match[2],{}).get('original_text') or ''
        checks['verbatim_quotes'] &= match[1] in original
    checks['no_model_urls']=not bool(re.search(r'https?://|www\.',generated,re.I))
    task=data.get('task') or {}
    event=task.get('fields',{}).get('event_date',{}).get('value','')
    if task.get('mode')=='general':lower=upper=date.today()
    else:lower,upper=date_bounds(event)
    for source in data.get('sources',[]):
        if source['source_type']=='legal_provision':
            pending = task.get('fields',{}).get('case_status',{}).get('value','')
            # Independent evaluation of the explicit transitional exception, not the production helper.
            transition = (source.get('temporal_rule') == 'pending_after_effective' and source.get('transition_text')
                          and re.search('尚未终审|未终审|没有生效裁判|未有生效裁判', pending)
                          and not re.search('已经终审|已终审|再审', pending)
                          and not re.search(r'是否|不(?:清楚|知道|确定|是)|可能|也许|或许|记不清|[?？]', pending)
                          and date.fromisoformat(source['effective_from']) <= date.today())
            checks['version_interval'] &= bool(lower and (date.fromisoformat(source['effective_from'])<=lower or transition) and
                (not source['effective_until'] or upper<date.fromisoformat(source['effective_until'])))
    for field in (task.get('fields') or {}).values():
        text=provenance.get(field['source_turn_id'],'')
        checks['field_provenance'] &= field['source']=='message' and field['quote'] in text and field['value'] in field['quote']
    checks['expected_missing']=set(expected.get('expected_missing',[])).issubset(data.get('missing_fields',[]))
    if expected.get('preserve_field'):
        checks['conflict_preserved']=expected['preserve_contains'] in task.get('fields',{}).get(expected['preserve_field'],{}).get('value','')
    for name,value in expected.get('field_contains',{}).items():
        checks['confirmed_field'] &= value in task.get('fields',{}).get(name,{}).get('value','')
    for call in trace:
        if call['task']=='TASK:APPLICABILITY':
            candidates=call['input'].get('candidates',[])
            candidate_ids=[known_sources[c['source_id']]['record_id'] for c in candidates if c['source_id'] in known_sources]
            candidate_by_label={c['source']['citation_id']:c for c in candidates if 'source' in c}
        if call['task']=='TASK:QA':
            selected_ids=[]
            for evidence in call['input'].get('evidence',[]):
                candidate=candidate_by_label.get(evidence['citation_id'])
                if candidate and not evidence.get('is_demo') and candidate['source_id'] in known_sources:
                    record=known_sources[candidate['source_id']]
                    if record['original_text']==evidence['text']:
                        selected_ids.append(record['record_id'])
    return {'observed_behavior':behavior,'checks':checks,'structural_passed':all(checks.values()),
            'candidate_ids':candidate_ids,'selected_ids':selected_ids,'returned_ids':returned,
            'candidate_metrics':ranking_metrics(candidate_ids,gold,5),
            'selected_metrics':ranking_metrics(selected_ids,gold,5),
            'returned_metrics':ranking_metrics(returned,gold,5),
            'semantic_review':'pending; structural checks do not establish faithfulness or legal correctness'}
