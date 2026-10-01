"""Generate a fresh candidate set after implementation freeze, without running it."""
import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
from app.core.config import BACKEND_DIR
from app.evaluation.dataset import sha256
from app.evaluation.once_acceptance import implementation_digest, load_package
from app.rag.catalog_profiles import profile_entries


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-directory',type=Path,required=True)
    args=parser.parse_args(); directory=args.output_directory.resolve()
    if directory.exists(): raise SystemExit('Choose a new package directory')
    old=[json.loads(line) for line in (BACKEND_DIR/'data/evaluation/rag-v1/queries.jsonl').read_text(encoding='utf-8').splitlines()]
    observed_sources={key for q in old for key in q['relevance']}
    observed_questions={q['query'] for q in old}
    names={'marriage_family':'婚姻家庭','labor_dispute':'劳动争议','traffic_accident':'交通事故','contract_dispute':'合同纠纷'}
    entries=profile_entries('eval-rag-v2-209'); random=secrets.SystemRandom();queries=[];scenarios=[];chosen=set()
    for domain, name in names.items():
        candidates=[e for e in entries if domain in e.verification.domains and e.record.record_id not in observed_sources and e.record.record_id not in chosen]
        random.shuffle(candidates)
        if len(candidates)<4: raise SystemExit(f'Not enough previously unlabelled provisions for {domain}')
        for index, entry in enumerate(candidates[:4],1):
            chosen.add(entry.record.record_id)
            keywords=entry.verification.keywords[:3]
            topic='、'.join(keywords) if keywords else entry.record.article_number
            message=f'请说明{name}中涉及{topic}的一般规则，只说明原文明示的主体、前提和例外，不涉及具体事件。'
            if message in observed_questions: raise ValueError('Question duplicates observed benchmark')
            qid=f'NEW-{domain}-{index:02}'
            queries.append({'id':qid,'route':'law','domain':domain,'split':'acceptance','scenario_group':f'new-topic-{entry.record.record_id}',
                'query':message,'category':'previously_unlabelled_provision','general':True,'expected_behavior':'answer',
                'relevance':{entry.record.record_id:{'grade':3,'rationale':'新候选问题由该条的核验关键词生成；直接金标准须独立核对具体争点。'}},
                'annotation_note':'候选标注待独立法律复核；排除旧集已标注来源不等于已证明语义主题互不重叠。','review_status':'agent_draft_pending_expert'})
            scenarios.append({'id':'E-'+qid,'query_id':qid,'domain':domain,'split':'acceptance','turns':[{'message':message,'expected':'answer'}],
                              'gold_sources':[entry.record.record_id],'review_status':'agent_draft_pending_expert'})
        for index, expected in ((5,'clarify'),(6,'insufficient')):
            message=(f'我有一个{name}问题，但还没有说清发生了什么、何时发生和想解决什么，帮我具体分析。' if expected=='clarify' else
                     f'我想了解{name}的一般信息，请给出未收录地区今年的地方补贴最新金额，不要用全国规则代替。')
            qid=f'NEW-{domain}-{index:02}'
            queries.append({'id':qid,'route':'law','domain':domain,'split':'acceptance','scenario_group':qid,'query':message,
                'category':'fact_or_corpus_boundary','general':expected=='insufficient','expected_behavior':expected,'relevance':{},
                'annotation_note':'明确缺事实或地方资料；预期行为仍须独立复核。','review_status':'agent_draft_pending_expert'})
            scenarios.append({'id':'E-'+qid,'query_id':qid,'domain':domain,'split':'acceptance','turns':[{'message':message,'expected':expected}],
                              'gold_sources':[],'review_status':'agent_draft_pending_expert'})
    random.shuffle(queries);random.shuffle(scenarios);directory.mkdir(parents=True)
    for name, data in (('queries.jsonl',queries),('scenarios.jsonl',scenarios)):
        with (directory/name).open('x',encoding='utf-8') as stream:
            stream.write(''.join(json.dumps(item,ensure_ascii=False)+'\n' for item in data))
    manifest={'version':'m4-once-candidate-v1','created_at':datetime.now(timezone.utc).isoformat(),'corpus_profile':'eval-rag-v2-209',
        'implementation_sha256':implementation_digest(),'query_count':len(queries),'scenario_count':len(scenarios),
        'domain_counts':dict(Counter(q['domain'] for q in queries)), 'unrun':True,'independent_blind_test':False,
        'author':'development_agent_generator','annotation_status':'agent_draft_pending_expert',
        'quality_gates': {'behavior_match_minimum':0.85, 'maximum_service_failures':0, 'maximum_hard_check_failures':0,
                          'semantic_review_required':True, 'expert_annotation_required':True},
        'files':{name:sha256(directory/name) for name in ('queries.jsonl','scenarios.jsonl')},
        'old_benchmark_manifest_sha256':sha256(BACKEND_DIR/'data/evaluation/rag-v1/manifest.json'),
        'limitations':['New exact questions and previously unlabelled provisions; topic independence is not expert-verified.',
                      'The same development agent wrote the generator; this is not an independent third-party blind test.']}
    (directory/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    load_package(directory)
    print(json.dumps({'created':True,'query_count':len(queries),'domain_counts':manifest['domain_counts'],'unrun':True,'independent_blind_test':False}))


if __name__=='__main__': main()
