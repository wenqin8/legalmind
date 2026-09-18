"""Explicit real-model smoke using only synthetic data and isolated local storage."""

import argparse
import asyncio
import json
import secrets
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx
from alembic import command
from alembic.config import Config
from fastapi.concurrency import run_in_threadpool

from app.core.config import BACKEND_DIR, Settings
from app.main import create_app
from app.rag.importer import import_cases, load_case_records
from app.rag.indexer import index_cases
from app.schemas.documents import TEMPLATES
from scripts.verify_postgres_week2 import _alembic_url


async def verify() -> dict:
    parent = BACKEND_DIR.parent / "tmp"
    parent.mkdir(exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="week3-model-", dir=parent))
    settings = Settings(environment="test", log_level="WARNING", llm_backend="deepseek", embedding_backend="sentence_transformers",
                        database_url=f"sqlite:///{(workspace / 'smoke.db').as_posix()}", chroma_persist_directory=workspace / "chroma")
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    with _alembic_url(settings.database_url.get_secret_value()):
        command.upgrade(config, "head")
    app = create_app(settings)
    import_cases(app.state.database, load_case_records(BACKEND_DIR / "data/demo/cases.jsonl"))
    summary = await run_in_threadpool(index_cases, app.state.database, app.state.vector_store, app.state.embedding_client)
    if summary.indexed != 16:
        raise RuntimeError("Synthetic indexing failed")
    report = {"embedding": settings.embedding_model_name, "model": settings.deepseek_model, "indexed_cases": 16, "checks": {}}
    user_id = None
    async with app.router.lifespan_context(app):
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", timeout=90) as client:
                username = "m3_" + uuid4().hex[:12]
                password = secrets.token_urlsafe(24)
                registered = await client.post("/api/v1/auth/register", json={"username": username, "email": username + "@example.com", "password": password})
                registered.raise_for_status()
                user_id = registered.json()["data"]["id"]
                login = await client.post("/api/v1/auth/login", json={"login": username, "password": password})
                login.raise_for_status()
                headers = {"Authorization": "Bearer " + login.json()["data"]["access_token"]}
                sid = None
                for name, question in (("qa", "公司三个月不发工资，没有完整劳动合同，我保存了考勤和工资转账，应该整理什么材料？"), ("followup", "针对刚才的情况，整理证据时有哪些风险和下一步？")):
                    started = time.monotonic()
                    answer = await client.post("/api/v1/chat/send", headers=headers, json={"message": question, "session_id": sid})
                    if answer.status_code != 200:
                        report["checks"][name] = {"ok": False, "status": answer.status_code, "code": answer.json().get("error", {}).get("code")}
                        return report
                    data = answer.json()["data"]
                    sid = data["session_id"]
                    report["checks"][name] = {"ok": data["intent"] == "qa" and bool(data["sources"]), "source_count": len(data["sources"]), "elapsed_seconds": round(time.monotonic() - started, 2)}
                    report[name + "_synthetic_response"] = data["response"]
                history = await client.get(f"/api/v1/chat/history/{sid}", headers=headers)
                report["checks"]["history"] = {"ok": len(history.json()["data"]["messages"]) == 4}
                stream = await client.post("/api/v1/chat/stream", headers=headers, json={"message": "请结合之前的问题，简要说明下一步", "session_id": sid})
                report["checks"]["stream_completion"] = {"ok": stream.status_code == 200 and '"success":true' in stream.text and "event: sources" in stream.text}
                report["stream_synthetic_response"] = stream.text
                for kind, template in TEMPLATES.items():
                    generated = await client.post("/api/v1/documents/generate", headers=headers, json={"document_type": kind, "parameters": {field.name: "合成验收信息（" + field.label + "）" for field in template.fields}, "use_references": False})
                    assert generated.status_code == 200
                    doc_id = generated.json()["data"]["document_id"]
                    for extension in ("md", "txt"):
                        download = await client.get(f"/api/v1/documents/{doc_id}/download?format={extension}", headers=headers)
                        assert download.status_code == 200 and download.text.startswith("草稿")
                    report["checks"][kind] = {"ok": True}
        finally:
            if user_id:
                store = app.state.session_store
                # Only this synthetic user's exact namespace is eligible for cleanup.
                keys = [key async for key in store.client.scan_iter(match=f"conversation:{user_id}:*")]
                if keys:
                    await store.client.delete(*keys)
                remaining = [key async for key in store.client.scan_iter(match=f"conversation:{user_id}:*")]
                report["redis_test_keys_removed"] = not remaining
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = asyncio.run(verify())
        report["passed"] = len(report["checks"]) == 7 and all(item["ok"] for item in report["checks"].values()) and report.get("redis_test_keys_removed", False)
    except Exception as exc:
        report = {"passed": False, "error_type": type(exc).__name__}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if not key.endswith("_synthetic_response")}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
