import json
import pytest
from app.evaluation.dataset import sha256
from app.evaluation.once_acceptance import load_package, consume_package, load_observed_package


def package(tmp_path, monkeypatch):
    monkeypatch.setattr('app.evaluation.once_acceptance.implementation_digest',lambda:'frozen')
    q={'id':'new','route':'law','domain':'labor_dispute','split':'acceptance','scenario_group':'new','query':'没有明确案情，请先问我','category':'boundary','expected_behavior':'clarify','relevance':{},'annotation_note':'待独立复核'}
    (tmp_path/'queries.jsonl').write_text(json.dumps(q)+'\n')
    (tmp_path/'scenarios.jsonl').write_text(json.dumps({'id':'E-new','query_id':'new','split':'acceptance',
        'domain':'labor_dispute', 'turns':[{'message': q['query'], 'expected':'clarify'}], 'gold_sources':[]})+'\n')
    manifest={'implementation_sha256':'frozen','query_count':1,'files':{f:sha256(tmp_path/f) for f in ('queries.jsonl','scenarios.jsonl')}}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    return tmp_path


def test_once_receipt_survives_failures_and_prevents_reuse(tmp_path, monkeypatch):
    p=package(tmp_path,monkeypatch);consume_package(p,tmp_path/'run.json')
    assert (p/'observation-receipt.json').exists()
    with pytest.raises(FileExistsError):consume_package(p,tmp_path/'run2.json')


def test_package_rejects_changed_inputs_and_changed_implementation(tmp_path,monkeypatch):
    p=package(tmp_path,monkeypatch)
    monkeypatch.setattr('app.evaluation.once_acceptance.implementation_digest',lambda:'changed')
    with pytest.raises(ValueError,match='Implementation'):load_package(p)
    monkeypatch.setattr('app.evaluation.once_acceptance.implementation_digest',lambda:'frozen')
    (p/'queries.jsonl').write_text('{}')
    with pytest.raises(ValueError,match='fingerprint'):load_package(p)


def test_observed_replay_requires_receipt_and_preserves_it_after_code_changes(tmp_path, monkeypatch):
    p = package(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='receipt'):load_observed_package(p)
    consume_package(p, tmp_path/'first.json')
    before = sha256(p/'observation-receipt.json')
    monkeypatch.setattr('app.evaluation.once_acceptance.implementation_digest', lambda:'new-code')
    assert len(load_observed_package(p)[1]) == 1
    assert sha256(p/'observation-receipt.json') == before
    (p/'queries.jsonl').write_text('{}')
    with pytest.raises(ValueError, match='fingerprint'):load_observed_package(p)


def test_observed_replay_rejects_changed_manifest(tmp_path, monkeypatch):
    p = package(tmp_path, monkeypatch)
    consume_package(p, tmp_path/'first.json')
    manifest = json.loads((p/'manifest.json').read_text())
    manifest['query_count'] = 2
    (p/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='receipt'):load_observed_package(p)


def test_package_rejects_mismatched_query_even_when_file_hashes_are_updated(tmp_path, monkeypatch):
    p = package(tmp_path, monkeypatch)
    scenario = json.loads((p/'scenarios.jsonl').read_text())
    scenario['turns'][0]['expected'] = 'answer'
    (p/'scenarios.jsonl').write_text(json.dumps(scenario)+'\n')
    manifest = json.loads((p/'manifest.json').read_text())
    manifest['files']['scenarios.jsonl'] = sha256(p/'scenarios.jsonl')
    (p/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='frozen query'):load_package(p)
