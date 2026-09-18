"""Verify real Redis semantics and PostgreSQL migrations using isolated resources."""

import asyncio
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import BACKEND_DIR, Settings
from app.db.models import Conversation, GeneratedDocument, User
from app.db.session import Database
from app.schemas.chat import ConversationMessage
from app.schemas.tasks import TaskState, GroundedValue
from app.rag.legal_catalog import load_catalog, import_catalog, retrieve_provisions
from app.services.session_store import RedisSessionStore, SessionBusy, SessionStoreUnavailable, history_key
from scripts.verify_postgres_week2 import _alembic_url, _safe_local_postgres_url


async def verify_redis(settings: Settings) -> dict:
    url = settings.redis_url.get_secret_value()
    if urlsplit(url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Only loopback verification is allowed")
    store = RedisSessionStore(url)
    key = history_key(uuid4(), uuid4())
    token = None
    result = {}
    try:
        assert await store.client.ping()
        token = await store.acquire(key, 30)
        try:
            await store.acquire(key, 30)
        except SessionBusy:
            result["mutual_exclusion"] = True
        empty = await store.snapshot(key, token)
        assert not empty.messages
        task = TaskState(kind="document", document_type="civil_complaint", fields={"plaintiff":GroundedValue(value="合成甲", quote="原告合成甲", source_turn_id=uuid4())})
        pair = [ConversationMessage(role=role, content="合成存储验收", created_at=datetime.now(timezone.utc), task=task if role == "assistant" else None).model_dump_json() for role in ("user", "assistant")]
        for _ in range(12):
            await store.append_pair(key, token, pair)
        full = await store.snapshot(key, token)
        assert len(full.messages) == 20
        assert ConversationMessage.model_validate_json(full.messages[-1]).task == task
        assert 86390 <= await store.client.ttl(key) <= 86400
        result.update(retention_20=True, sliding_ttl_24h=True, structured_state_roundtrip=True)
        try:
            await store.append_pair(key, "wrong-token", pair)
        except SessionStoreUnavailable:
            result["write_fencing"] = True
        assert (await store.snapshot(key, token)).messages == full.messages
        await store.delete(key, token)
        await store.restore(key, token, full)
        assert (await store.snapshot(key, token)).messages == full.messages
        result["compensation_restore"] = True
        await store.client.pexpire(key, 50)
        await asyncio.sleep(0.08)
        assert not (await store.snapshot(key, token)).messages
        result["expiration"] = True
        await store.restore(key, token, empty)
    finally:
        if token:
            await store.delete(key, token)
            await store.release(key, token)
            result["keys_removed"] = not await store.client.exists(key, key + ":lock")
        await store.aclose()
    assert all(result.values()) and len(result) == 8
    return result


def verify_postgres(settings: Settings) -> dict:
    if not settings.postgres_smoke_url:
        raise RuntimeError("PostgreSQL smoke URL not configured")
    admin_url = _safe_local_postgres_url(settings.postgres_smoke_url.get_secret_value())
    engine = create_engine(admin_url, connect_args={"connect_timeout": 3})
    schema = "legalmind_m3_" + uuid4().hex
    created = False
    database = None
    result = {}
    try:
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        created = True
        url = admin_url.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
        with _alembic_url(url):
            command.upgrade(config, "head")
            command.check(config)
        database = Database(url)
        columns = {column["name"]: column["type"].__class__.__name__ for column in inspect(database.engine).get_columns("generated_documents")}
        assert columns["parameters"] == columns["sources"] == "JSONB"
        owner, other, doc_id = uuid4(), uuid4(), uuid4()
        with database.session() as session, session.begin():
            session.add(User(id=owner, username="m3_test", username_normalized="m3_test", email="m3@example.com", email_normalized="m3@example.com", password_hash="synthetic-unused-hash"))
            session.flush()
            session.add(GeneratedDocument(id=doc_id, user_id=owner, document_type="general_contract", title="合成草稿", content="草稿", parameters={"party_a": "甲"}, additional_instructions="", sources=[]))
            session.add(Conversation(id=doc_id, user_id=owner, title="合成咨询", history_commit_id=doc_id))
        with database.session() as session:
            assert session.scalar(select(GeneratedDocument).where(GeneratedDocument.id == doc_id, GeneratedDocument.user_id == owner)) is not None
            assert session.scalar(select(GeneratedDocument).where(GeneratedDocument.id == doc_id, GeneratedDocument.user_id == other)) is None
            assert session.get(Conversation, doc_id).history_commit_id == doc_id
        result.update(jsonb=True, document_roundtrip=True, owner_filter=True, history_commit_marker=True)
        import_catalog(database, load_catalog(BACKEND_DIR / "data/legal/verified_provisions.jsonl"))
        assert retrieve_provisions(database, "合同违约", "contract_dispute", event_date="2025年")
        verification_type = next(c["type"].__class__.__name__ for c in inspect(database.engine).get_columns("legal_provisions") if c["name"] == "verification")
        assert verification_type == "JSONB"
        result.update(verified_laws_jsonb=True, verified_laws_roundtrip=True)
        database.dispose()
        database = None
        with _alembic_url(url):
            command.downgrade(config, "base")
            command.upgrade(config, "head")
        result["upgrade_downgrade_upgrade"] = True
    finally:
        if database:
            database.dispose()
        if created:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True, if_exists=True))
                result["schema_removed"] = connection.scalar(text("SELECT count(*) FROM information_schema.schemata WHERE schema_name=:schema"), {"schema": schema}) == 0
        engine.dispose()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = Settings()
    results = {}
    for name, check in (("redis", lambda: asyncio.run(verify_redis(settings))), ("postgresql", lambda: verify_postgres(settings))):
        try:
            results[name] = {"ok": True, "checks": check()}
        except Exception as exc:
            results[name] = {"ok": False, "error_type": type(exc).__name__}
    print(json.dumps(results, ensure_ascii=False, indent=2))
    passed = all(value["ok"] for value in results.values())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(), "checks": results, "passed": passed}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
