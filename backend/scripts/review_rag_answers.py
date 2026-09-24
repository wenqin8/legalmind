"""Re-score saved synthetic responses offline; no model calls or baseline overwrites."""

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean

from app.evaluation.answers import check_turn
from app.evaluation.dataset import load_queries, catalog_entries, sha256
from app.rag.importer import normalize_legal_provision
from app.rag.catalog_profiles import profile_entries


def known_sources():
    known={}
    for entry in profile_entries('eval-rag-v2-209'):
        record=normalize_legal_provision(entry.record)
        known[str(record.id)]={'record_id':record.record_id,'title':record.regulation_name,'reference_number':record.article_number,
            'source_url':record.source_url,**{k:entry.verification.model_dump(mode='json').get(k) for k in
                ('version','original_text','effective_from','effective_until','verified_at','status_as_of')}}
    return known


def review(raw: dict, annotations: dict | None = None):
    queries={q.id:q for q in load_queries()};known=known_sources();items=[]
    for scenario in raw['scenarios']:
        query=queries[scenario['query_id']]
        item={'id':scenario['id'],'domain':scenario['domain'],'split':scenario['split'],
              'gold_grades':{key:value.grade for key,value in query.relevance.items()},'turns':[]}
        for index,turn in enumerate(scenario['turns'],1):
            entry={'turn':index,'expected':turn['expected']['expected'],'status':turn.get('status'),'error':turn.get('error')}
            if turn.get('status')==200 and turn.get('evaluation'):
                evaluation=check_turn(turn['response'],turn['expected'],known,turn.get('model_trace',[]),{k:v.grade for k,v in query.relevance.items()}, {})
                # Original runner verified provenance against HTTP history. Do not infer message IDs from model output.
                evaluation['checks']['field_provenance']=turn['evaluation']['checks']['field_provenance']
                evaluation['structural_passed']=all(evaluation['checks'].values())
                evaluation['provenance_check_origin']='original HTTP history check, carried forward unchanged'
                entry['evaluation']=evaluation
            else:
                entry['failure_stage']='generation_or_service' if any(c['task']=='TASK:QA' for c in turn.get('model_trace',[])) else 'upstream_or_service'
                # A downstream generation error must not erase an observed successful retrieval.
                stages=check_turn({},turn['expected'],known,turn.get('model_trace',[]),{k:v.grade for k,v in query.relevance.items()}, {})
                entry['stage_metrics']={k:v for k,v in stages.items() if k.endswith('_metrics') or k.endswith('_ids')}
            item['turns'].append(entry)
        item['agent_review']=(annotations or {}).get(scenario['id'],{'status':'pending_expert_review'})
        items.append(item)
    turns=[t for s in items for t in s['turns']]
    answered=[t for t in turns if t['expected']=='answer']
    successes=[t for t in turns if 'evaluation' in t]
    def fraction(rows,predicate):return {'value':sum(predicate(t) for t in rows)/len(rows) if rows else None,'denominator':len(rows)}
    metrics={'planned_turns':len(turns),'http_successes':len(successes),'scenario_structural_passes':sum(all(t.get('evaluation',{}).get('structural_passed',False) for t in s['turns']) for s in items),
        'expected_answer_behavior_counts':dict(Counter(t.get('evaluation',{}).get('observed_behavior','service_error') for t in answered)),
        'behavior_match_including_errors':fraction(turns,lambda t:t.get('evaluation',{}).get('checks',{}).get('expected_behavior',False)),
        'answerable_but_insufficient_rate':fraction(answered,lambda t:t.get('evaluation',{}).get('observed_behavior')=='insufficient'),
        'answerable_but_clarifying_rate':fraction(answered,lambda t:t.get('evaluation',{}).get('observed_behavior')=='clarify'),
        'hard_check_failures':{name:sum(not t['evaluation']['checks'][name] for t in successes)
            for name in ('source_integrity','known_citations','verbatim_quotes','no_model_urls','version_interval','field_provenance','conflict_preserved','confirmed_field')}}
    for stage in ('candidate','selected','returned'):
        # Include every expected-answer turn; retain measured earlier stages on downstream errors.
        for name in ('hit','recall'):
            values=[(t.get('evaluation') or t.get('stage_metrics',{})).get(stage+'_metrics',{}).get(name) or 0 for t in answered]
            metrics[f'{stage}_{name}_on_expected_answers']={'value':mean(values) if values else None,'denominator':len(values)}
    metrics['by_domain']={}
    metrics['source_recall_by_grade']={}
    for grade in (3,2,1):
        rows=[(turn, {key for key,value in item['gold_grades'].items() if value==grade})
              for item in items for turn in item['turns'] if turn['expected']=='answer']
        rows=[(turn,gold) for turn,gold in rows if gold]
        stages={}
        for stage in ('candidate','selected','returned'):
            matches=[len(set((turn.get('evaluation') or turn.get('stage_metrics',{})).get(stage+'_ids',[])) & gold)
                     for turn,gold in rows]
            stages[stage]={'macro_recall':mean(n/len(gold) for n,(_,gold) in zip(matches,rows)) if rows else None,
                           'turns_with_grade':len(rows), 'matched_sources':sum(matches),
                           'gold_sources':sum(len(gold) for _,gold in rows)}
        metrics['source_recall_by_grade'][str(grade)]=stages
    for domain in sorted({s['domain'] for s in items}):
        subset=[t for s in items if s['domain']==domain for t in s['turns']]
        metrics['by_domain'][domain]={'turns':len(subset),
            'behavior_match_including_errors':fraction(subset,lambda t:t.get('evaluation',{}).get('checks',{}).get('expected_behavior',False)),
            'http_successes':sum('evaluation' in t for t in subset)}
    return {'source_run_started_at':raw['started_at'],'complete':raw['complete'],'model_reruns':0,
            'annotation_status':'agent_review_not_expert_certification','quality_gate_passed':False if any(metrics['hard_check_failures'].values()) else None,
            'metrics':metrics,'items':items}


def render(report):
    lines=['# RAG 端到端复核','',f"本报告从原始{len(report['items'])}场景输出离线复算，不重新调用模型、不修改冻结标签。",
           '结构校验与开发代理语义复核分别记录；尚无法律专家审核，不给出法律正确率认证。','',
           '## 自动化指标','', '```json',json.dumps(report['metrics'],ensure_ascii=False,indent=2),'```','',
           '## 逐场景复核','']
    for item in report['items']:
        lines.append(f"### {item['id']}")
        lines.append('')
        for turn in item['turns']:
            ev=turn.get('evaluation',{})
            failures=[k for k,v in ev.get('checks',{}).items() if not v]
            lines.append(f"- 第 {turn['turn']} 轮：预期 {turn['expected']}；实际 {ev.get('observed_behavior',turn.get('error'))}；未通过项：{', '.join(failures) or '无'}。")
        note=item['agent_review']
        for key in ('faithfulness','applicability','diagnosis','annotation_caveat'):
            if note.get(key):lines.append(f"- {key}：{note[key]}")
        lines.append('')
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--annotations',type=Path)
    args=parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.md').exists():raise SystemExit('Choose a new output path')
    annotations=json.loads(args.annotations.read_text(encoding='utf-8')) if args.annotations else None
    report=review(json.loads(args.input.read_text(encoding='utf-8')),annotations)
    report['raw_report_sha256']=sha256(args.input)
    report['review_implementation_sha256']=sha256(Path(__file__))
    report['annotations_sha256']=sha256(args.annotations) if args.annotations else None
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    args.output.with_suffix('.md').write_text(render(report),encoding='utf-8')
    print(json.dumps(report['metrics'],ensure_ascii=False))


if __name__=='__main__':main()
