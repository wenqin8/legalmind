import json
import math
from collections import Counter
from pathlib import Path

import pytest

from app.evaluation.dataset import BENCHMARK_DIR, catalog_entries, load_queries, sha256
from app.evaluation.metrics import aggregate, percentile, ranking_metrics
from app.evaluation.environment import prepare


def test_metrics_use_complete_relevance_and_fixed_precision_denominator():
    values=ranking_metrics(['b','x','a'],{'a':3,'b':1,'c':2},5)
    assert values['hit']==1 and values['recall']==pytest.approx(2/3)
    assert values['precision']==pytest.approx(2/5) and values['reciprocal_rank']==1
    expected=(1+7/math.log2(4))/(7+3/math.log2(3)+1/math.log2(4))
    assert values['ndcg']==pytest.approx(expected)
    assert ranking_metrics(['a'],{'a':3,'b':2,'c':1,'d':1},3)['recall_ceiling']==.75


def test_negatives_and_empty_outputs_are_not_false_perfect_scores():
    values=ranking_metrics([],{},5)
    assert values['hit'] is values['recall'] is values['ndcg'] is None
    assert values['precision']==0 and values['negative_false_retrieval'] is False
    assert ranking_metrics(['a'],{},5)['negative_false_retrieval'] is True
    assert ranking_metrics([],{'a':3},5)['recall']==0
    with pytest.raises(ValueError): ranking_metrics(['a','a'],{'a':3},5)
    with pytest.raises(ValueError): ranking_metrics(['a'],{'a':0},5)


def test_errors_stay_in_effective_success_denominator():
    rows=[{'answerable':True,'error':None,'latency_ms':10,'metrics':{str(k):ranking_metrics(['a'],{'a':3},k) for k in (1,3,5)}},
          {'answerable':True,'error':'TimeoutError','latency_ms':100,'metrics':{}}]
    result=aggregate(rows)
    assert result['effective_hit@5_including_errors']=={'value':.5,'denominator':2}
    assert result['service_errors']==1 and result['hit@5']['denominator']==1
    assert percentile([10,20,30],.95)==29
    assert aggregate([])['hit@5']['value'] is None


def test_frozen_queries_have_balanced_groups_valid_sources_and_scenarios():
    rows=load_queries()
    assert Counter((r.route,r.domain,r.split) for r in rows)==Counter({(route,domain,split):count
        for route in ('case','law') for domain in ('marriage_family','labor_dispute','traffic_accident','contract_dispute')
        for split,count in [('development',15),('holdout',5)]})
    scenarios=[json.loads(line) for line in (BENCHMARK_DIR/'scenarios.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(scenarios)==40 and sum(len(s['turns'])>1 for s in scenarios)==12
    assert all(s['query_id'] in {r.id for r in rows} for s in scenarios)
    assert len({s['id'] for s in scenarios})==40
    by_id={r.id:r for r in rows}
    assert all(s['gold_sources']==list(by_id[s['query_id']].relevance) for s in scenarios)


def test_expansion_contains_complete_clean_official_article_snapshots():
    entries=catalog_entries()
    assert len(entries)==197 and len({e.record.record_id for e in entries})==197
    folder=Path('data/legal/expansion-v1')
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    assert sha256(folder/'verified_provisions.jsonl')==manifest['catalog_sha256']
    for source in manifest['sources']:
        path=folder/source['snapshot']
        assert sha256(path)==source['sha256']
        text=path.read_text(encoding='utf-8')
        assert not any(mark in text for mark in ('责任编辑','相关链接','新闻链接','京ICP备'))
        matching=[e for e in entries if str(e.record.source_url)==source['source_url']]
        assert len(matching)==source['articles']
        assert all(e.verification.original_text in text for e in matching)
    transition=next(e for e in entries if e.record.record_id=='contract_general-2023-12-04-69')
    assert '尚未终审' in transition.verification.original_text


def test_changed_query_artifact_is_rejected(tmp_path,monkeypatch):
    from app.evaluation import dataset
    original=dataset.sha256
    monkeypatch.setattr(dataset,'sha256',lambda path:'bad' if path.name=='queries.jsonl' else original(path))
    with pytest.raises(ValueError,match='Frozen artifact mismatch'):load_queries()


def test_evaluation_cannot_write_outside_isolated_workspace(tmp_path):
    with pytest.raises(ValueError,match='tmp directory'):prepare(tmp_path)
