"""Run frozen development queries against an explicitly selected corpus profile."""

import argparse
import json
import time
from datetime import datetime, timezone, date
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.core.config import BACKEND_DIR
from app.db.models import Case
from app.evaluation.dataset import load_queries
from app.evaluation.environment import prepare, provenance
from app.evaluation.metrics import aggregate, ranking_metrics
from app.rag.legal_catalog import retrieve_provisions
from app.rag.catalog_profiles import catalog_identity
from app.rag.retriever import reciprocal_rank_fusion, BM25_K1, BM25_B, RRF_K, PER_ROUTE_CANDIDATES, VECTOR_CHUNK_CANDIDATES


def render_report(report: dict) -> str:
    text = ['# RAG 检索评估', '', '相关性为冻结查询的开发代理标注草案，未经法律专家复核。空标签题不进入 Recall/MRR/NDCG 分母。', '',
            '| 分组 | 题数 | Hit@5 | Recall@5 | Precision@5 | MRR@5 | NDCG@5 | 无答案误召回率 | P95 ms |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    def value(group, name):
        v = group[name]['value']; return 'N/A' if v is None else f'{v:.3f}'
    for name, group in report['groups'].items():
        text.append('| '+name+' | '+str(group['queries'])+' | '+' | '.join(value(group,k) for k in
                    ('hit@5','recall@5','precision@5','reciprocal_rank@5','ndcg@5','negative_false_retrieval@5'))+
                    f" | {group['latency_ms_p95']:.1f} |" if group['latency_ms_p95'] is not None else f'| {name} | 服务故障 |')
    text += ['', 'Precision@K 分母固定为 K，缺少返回项不补分；无答案题的正例排序指标为空。每项指标的精确分母见 JSON。',
             '版本匹配率仅检查固定元数据的日期区间，不证明司法解释过渡适用正确。案例路线不作日期版本判分。',
             '计时不含资料导入、建索引和权重加载；记录本机顺序查询耗时，首次查询可能包含缓存开销。不是并发负载测试。案例参数冻结；法条候选策略见 JSON 配置。', '', '## 失败明细', '']
    failures = [r for r in report['results'] if r['error'] or (r['answerable'] and r['metrics']['5']['recall'] < 1) or
                (not r['answerable'] and r['ranking']) or not all(r.get('version_checks', []))]
    for row in failures:
        text.append(f"- `{row['id']}` / {row['route']}: " + (row['error'] or
                    ('无答案题返回候选' if not row['answerable'] else '相关资料未全部进入 Top-5')))
    text += ['', '以上是基线发现，不通过改标签或重跑挑选较好成绩消除失败。']
    return '\n'.join(text)+'\n'


def evaluate(split: str = 'development', corpus_profile: str = 'eval-rag-v2-209') -> dict:
    queries = [q for q in load_queries() if split == 'all' or q.split == split]
    workspace = BACKEND_DIR.parent/'tmp'/('rag-retrieval-'+uuid4().hex)
    started = datetime.now(timezone.utc).isoformat()
    settings, database, embedding, store, retriever = prepare(workspace, corpus_profile)
    results = []
    try:
        with database.session() as session:
            ids = {row.id:row.case_number for row in session.scalars(select(Case))}
        for query in queries:
            base={'id':query.id,'domain':query.domain,'split':query.split,'category':query.category,
                  'answerable':bool(query.relevance),'gold':{k:v.grade for k,v in query.relevance.items()}}
            t0=time.perf_counter()
            routes={}
            error=None
            try:
                if query.route=='case':
                    t=time.perf_counter(); vector=retriever._vector_ranked_sources(query.query,None,None)
                    vt=(time.perf_counter()-t)*1000
                    t=time.perf_counter(); bm25=retriever._bm25_ranked_sources(query.query,None,None)
                    bt=(time.perf_counter()-t)*1000
                    fused=reciprocal_rank_fusion(vector,bm25)
                    routes={'case_vector':([ids[x] for x in vector[:5]],vt,[]),
                            'case_bm25':([ids[x] for x in bm25[:5]],bt,[]),
                            'case_hybrid':([ids[x[0]] for x in fused[:5]],(time.perf_counter()-t0)*1000,[])}
                else:
                    rows=retrieve_provisions(database,query.query,query.domain,event_date=query.event_date,general=query.general)
                    valid=[]
                    for _,version in rows:
                        if query.general:
                            first=last=date.today()
                        elif query.event_start:
                            first=date.fromisoformat(query.event_start); last=date.fromisoformat(query.event_end)
                        else:
                            valid.append(False); continue
                        valid.append(version.effective_from<=first and (version.effective_until is None or last<version.effective_until))
                    routes={'law_bm25':([r.record_id for r,_ in rows],(time.perf_counter()-t0)*1000,valid)}
            except Exception as exc:
                error=type(exc).__name__
                routes={key:([],(time.perf_counter()-t0)*1000,[]) for key in
                        (('case_vector','case_bm25','case_hybrid') if query.route=='case' else ('law_bm25',))}
            for route,(ranking,elapsed,versions) in routes.items():
                results.append({**base,'route':route,'ranking':ranking,'latency_ms':round(elapsed,3),'error':error,
                    'version_checks':versions,'metrics':{str(k):ranking_metrics(ranking,base['gold'],k) for k in (1,3,5)} if not error else {}})
        groups={}
        for route in sorted({r['route'] for r in results}):
            subset=[r for r in results if r['route']==route]
            groups[route]=aggregate(subset)
            for field in ('split','domain','category'):
                for value in sorted({r[field] for r in subset}):
                    groups[f'{route}/{field}/{value}']=aggregate([r for r in subset if r[field]==value])
        return {'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'scope':'frozen development queries; explicit corpus profile; not blind acceptance',
                'complete':len(results)==sum(3 if q.route=='case' else 1 for q in queries),
                'quality_gate_passed':None,'annotation_status':'agent_draft_pending_expert','configuration':provenance(settings),
                'catalog':catalog_identity(database), 'split':split,
                'retrieval_parameters':{'bm25_k1':BM25_K1,'bm25_b':BM25_B,'rrf_k':RRF_K,'route_candidates':PER_ROUTE_CANDIDATES,
                    'vector_chunk_pool':VECTOR_CHUNK_CANDIDATES,'top_k':5,'case_domain_filter':None,'law_domain_filter':'gold domain supplied',
                    'law_candidate_policy':'top 3 BM25 preserved; remaining 2 selected by score/(1+same regulation count)'},
                'groups':groups,'results':results}
    finally:
        database.dispose()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--split',choices=['development'],default='development')
    parser.add_argument('--corpus-profile',choices=['eval-rag-v1-197','eval-rag-v2-209'],default='eval-rag-v2-209')
    args=parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.md').exists():
        raise SystemExit('Refusing to overwrite a prior baseline; choose a new output path')
    report=evaluate(args.split,args.corpus_profile)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    args.output.with_suffix('.md').write_text(render_report(report),encoding='utf-8')
    print(json.dumps({'complete':report['complete'],'groups':{k:v for k,v in report['groups'].items() if '/' not in k}},ensure_ascii=False))
    return 2 if any(r['error'] for r in report['results']) else 0


if __name__=='__main__':
    raise SystemExit(main())
