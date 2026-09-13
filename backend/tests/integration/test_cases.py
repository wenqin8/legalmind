import logging
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.core.enums import ImportStatus
from app.db.models import Case
from app.rag.importer import import_cases, load_case_records
from app.rag.indexer import index_cases
from app.rag.retriever import RetrievalError

pytestmark = pytest.mark.anyio

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "cases.jsonl"
PASSWORD = "correct horse battery staple"


async def _token(client: httpx.AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "case_user",
            "email": "case@example.com",
            "password": PASSWORD,
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"login": "case_user", "password": PASSWORD},
    )
    return response.json()["data"]["access_token"]


def _build_index(app: FastAPI) -> None:
    import_cases(app.state.database, load_case_records(DATASET_PATH))
    summary = index_cases(
        app.state.database,
        app.state.vector_store,
        app.state.embedding_client,
    )
    assert summary.indexed == 16


async def test_case_routes_require_jwt(client: httpx.AsyncClient) -> None:
    search = await client.post("/api/v1/cases/search", json={"query": "拖欠工资"})
    detail = await client.get(f"/api/v1/cases/{uuid4()}")

    assert search.status_code == detail.status_code == 401
    assert search.json()["error"]["code"] == "AUTH_REQUIRED"


async def test_search_and_detail_return_relational_source_truth(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    _build_index(app)
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/cases/search",
        headers=headers,
        json={"query": "公司没有签劳动合同还拖欠几个月工资", "top_k": 5},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert 1 <= data["count"] <= 5
    assert data["items"][0]["case_number"] == "DEMO-LABOR_DISPUTE-001"
    assert data["items"][0]["court"] is None
    assert data["items"][0]["source_url"] is None
    assert data["items"][0]["is_demo"] is True
    assert "不表示法律结论置信度" in data["score_note"]

    detail = await client.get(
        f"/api/v1/cases/{data['items'][0]['id']}", headers=headers
    )
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert detail_data["facts"]
    assert detail_data["dispute_focus"]
    assert detail_data["reasoning"]
    assert detail_data["warning"] == "课程演示合成数据，不是真实判例或法律依据"


async def test_filters_top_k_empty_route_and_unknown_detail(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    _build_index(app)
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    filtered = await client.post(
        "/api/v1/cases/search",
        headers=headers,
        json={
            "query": "证据争议",
            "domain": "traffic_accident",
            "source_kind": "demo",
            "top_k": 2,
        },
    )
    no_source = await client.post(
        "/api/v1/cases/search",
        headers=headers,
        json={"query": "拖欠工资", "source_kind": "official"},
    )
    missing = await client.get(f"/api/v1/cases/{uuid4()}", headers=headers)

    assert filtered.status_code == 200
    assert 0 < filtered.json()["data"]["count"] <= 2
    assert {
        item["domain"] for item in filtered.json()["data"]["items"]
    } == {"traffic_accident"}
    assert no_source.status_code == 200
    assert no_source.json()["data"] == {
        "items": [],
        "count": 0,
        "score_note": "rrf_score 仅表示检索排序依据，不表示法律结论置信度",
    }
    assert missing.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "   "},
        {"query": "a" * 1001},
        {"query": "案例", "domain": "criminal"},
        {"query": "案例", "source_kind": "unknown"},
        {"query": "案例", "top_k": 0},
        {"query": "案例", "top_k": 21},
        {"query": "案例", "extra": True},
    ],
)
async def test_case_search_rejects_invalid_input(
    client: httpx.AsyncClient,
    payload: dict[str, object],
) -> None:
    token = await _token(client)
    response = await client.post(
        "/api/v1/cases/search",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_stale_chroma_metadata_is_not_used_as_display_truth(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    _build_index(app)
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with app.state.database.session() as session:
        case = session.scalar(select(Case).where(Case.case_number == "DEMO-LABOR_DISPUTE-001"))
        assert case is not None
        case.title = "关系库事实标题"
        session.commit()

    response = await client.post(
        "/api/v1/cases/search",
        headers=headers,
        json={"query": "拖欠工资劳动关系证明"},
    )

    assert response.status_code == 200
    match = next(
        item
        for item in response.json()["data"]["items"]
        if item["case_number"] == "DEMO-LABOR_DISPUTE-001"
    )
    assert match["title"] == "关系库事实标题"


async def test_retrieval_failure_is_sanitized_and_query_is_not_logged(
    client: httpx.AsyncClient,
    app: FastAPI,
    caplog,
) -> None:
    token = await _token(client)
    secret_query = "private-query-that-must-not-be-logged"

    def fail(*args, **kwargs):
        raise RetrievalError("raw model path and internal detail")

    app.state.embedding_client.embed_query = fail
    caplog.set_level(logging.INFO)
    response = await client.post(
        "/api/v1/cases/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": secret_query},
    )

    assert response.status_code == 424
    assert response.json()["error"]["code"] == "RETRIEVAL_UNAVAILABLE"
    assert "raw model path" not in response.text
    assert secret_query not in caplog.text


async def test_pending_case_is_excluded_from_detail_and_search(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    _build_index(app)
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with app.state.database.session() as session:
        case = session.scalar(select(Case).where(Case.case_number == "DEMO-LABOR_DISPUTE-001"))
        assert case is not None
        case_id = case.id
        case.import_status = ImportStatus.PENDING
        session.commit()

    detail = await client.get(f"/api/v1/cases/{case_id}", headers=headers)
    search = await client.post(
        "/api/v1/cases/search",
        headers=headers,
        json={"query": "拖欠工资劳动关系证明", "top_k": 20},
    )

    assert detail.status_code == 404
    assert all(item["id"] != str(case_id) for item in search.json()["data"]["items"])


async def test_hybrid_search_keeps_results_when_either_route_is_empty(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    _build_index(app)
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    original_query = app.state.vector_store.query
    app.state.vector_store.query = lambda *args, **kwargs: {"metadatas": [[]]}
    bm25_only = await client.post(
        "/api/v1/cases/search",
        headers=headers,
        json={"query": "拖欠工资劳动关系证明"},
    )
    app.state.vector_store.query = original_query

    original_bm25 = app.state.case_retriever._bm25_ranked_sources
    app.state.case_retriever._bm25_ranked_sources = lambda *args, **kwargs: []
    vector_only = await client.post(
        "/api/v1/cases/search",
        headers=headers,
        json={"query": "房屋租赁押金返还"},
    )
    app.state.case_retriever._bm25_ranked_sources = original_bm25

    assert bm25_only.status_code == vector_only.status_code == 200
    assert bm25_only.json()["data"]["count"] > 0
    assert vector_only.json()["data"]["count"] > 0
    assert all(
        item["vector_rank"] is None for item in bm25_only.json()["data"]["items"]
    )
    assert all(
        item["bm25_rank"] is None for item in vector_only.json()["data"]["items"]
    )


async def test_embedding_runtime_error_maps_to_sanitized_424(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    _build_index(app)
    token = await _token(client)

    def fail(_: str) -> list[float]:
        raise RuntimeError("private model cache path")

    app.state.embedding_client.embed_query = fail
    response = await client.post(
        "/api/v1/cases/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "拖欠工资"},
    )

    assert response.status_code == 424
    assert response.json()["error"]["code"] == "RETRIEVAL_UNAVAILABLE"
    assert "private model cache path" not in response.text
