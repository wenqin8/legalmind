from uuid import uuid4

import pytest

from app.schemas.documents import TEMPLATES
from tests.integration.test_chat import _create_user_token

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("kind", list(TEMPLATES))
async def test_document_generation_missing_fields_download_and_ownership(client, app, kind):
    owner = await _create_user_token(client, suffix="doc_owner")
    other = await _create_user_token(client, suffix="doc_other")
    headers = {"Authorization": f"Bearer {owner}"}
    templates = await client.get("/api/v1/documents/templates", headers=headers)
    assert len(templates.json()["data"]["items"]) == 3
    payload = {"document_type": kind, "parameters": {}, "use_references": False}
    missing = await client.post("/api/v1/documents/generate", headers=headers, json=payload)
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "DOCUMENT_FIELDS_MISSING"
    payload["parameters"] = {field.name: f"用户提供{field.label}" for field in TEMPLATES[kind].fields}
    generated = await client.post("/api/v1/documents/generate", headers=headers, json=payload)
    assert generated.status_code == 200
    data = generated.json()["data"]
    assert data["content"].startswith("草稿，提交或签署前须人工审核")
    assert data["sources"] == []
    for format in ("md", "txt"):
        downloaded = await client.get(f'/api/v1/documents/{data["document_id"]}/download?format={format}', headers=headers)
        assert downloaded.status_code == 200
        assert f'.{format}"' in downloaded.headers["content-disposition"]
        assert "用户提供" in downloaded.text
    forbidden = await client.get(f'/api/v1/documents/{data["document_id"]}/download', headers={"Authorization": f"Bearer {other}"})
    assert forbidden.status_code == 404
    assert app.state.llm_client.call_count == 0


async def test_invalid_document_parameters_and_auth(client):
    assert (await client.get("/api/v1/documents/templates")).status_code == 401
    token = await _create_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    for parameters in ({"unknown": "x"}, {"plaintiff": 123}, {"plaintiff": "x" * 21000}):
        result = await client.post("/api/v1/documents/generate", headers=headers, json={"document_type": "civil_complaint", "parameters": parameters, "use_references": False})
        assert result.status_code == 422
    assert (await client.get(f"/api/v1/documents/{uuid4()}/download?format=pdf", headers=headers)).status_code == 422
