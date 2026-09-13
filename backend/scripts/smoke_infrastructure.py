"""Run isolated connectivity checks for the M1 infrastructure dependencies."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit
from uuid import uuid4

import chromadb
import psycopg
import redis
from chromadb.config import Settings as ChromaSettings

from app.core.config import Settings


def smoke_postgres(url: str) -> dict[str, Any]:
    with psycopg.connect(url, connect_timeout=5, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1, current_setting('server_version')")
            row = cursor.fetchone()
    if row is None or row[0] != 1:
        raise RuntimeError("PostgreSQL did not return the expected probe value")
    return {"ok": True, "server_version": str(row[1])}


def smoke_redis(url: str) -> dict[str, Any]:
    client = redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    key = f"legalmind:m1:smoke:{uuid4().hex}"
    try:
        if client.ping() is not True:
            raise RuntimeError("Redis PING did not return true")
        client.set(key, "ok", ex=30)
        if client.get(key) != "ok":
            raise RuntimeError("Redis round-trip value did not match")
        server_version = client.info("server").get("redis_version", "unknown")
        return {"ok": True, "server_version": str(server_version)}
    finally:
        try:
            client.delete(key)
        finally:
            client.close()


def smoke_chroma(persist_directory: Path) -> dict[str, Any]:
    persist_directory.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(persist_directory),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection_name = f"legalmind_m1_smoke_{uuid4().hex}"
    collection = client.create_collection(collection_name)
    document_id = uuid4().hex
    try:
        collection.add(
            ids=[document_id],
            embeddings=[[1.0, 0.0, 0.0]],
            documents=["LegalMind M1 infrastructure smoke test"],
            metadatas=[{"kind": "smoke"}],
        )
        result = collection.query(query_embeddings=[[1.0, 0.0, 0.0]], n_results=1)
        if result.get("ids") != [[document_id]]:
            raise RuntimeError("Chroma persistent round-trip did not return the probe document")
        heartbeat = client.heartbeat()
        return {
            "ok": True,
            "heartbeat": int(heartbeat),
            "persist_directory": str(persist_directory),
        }
    finally:
        client.delete_collection(collection_name)


def _safe_error(error: Exception, secret_values: tuple[str, ...]) -> str:
    message = f"{type(error).__name__}: {error}"
    for value in secret_values:
        if value:
            message = message.replace(value, "<redacted>")
    return message


def _redaction_values(*urls: str) -> tuple[str, ...]:
    values: list[str] = []
    for url in urls:
        if not url:
            continue
        values.append(url)
        password = urlsplit(url).password
        if password:
            values.append(password)
    return tuple(values)


def _missing_postgres_url() -> dict[str, Any]:
    raise RuntimeError("LEGALMIND_POSTGRES_SMOKE_URL is not configured")


def main() -> int:
    settings = Settings()
    postgres_url = (
        settings.postgres_smoke_url.get_secret_value()
        if settings.postgres_smoke_url is not None
        else ""
    )
    redis_url = settings.redis_url.get_secret_value()
    secrets_to_redact = _redaction_values(postgres_url, redis_url)

    checks: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
        (
            "postgresql",
            lambda: smoke_postgres(postgres_url) if postgres_url else _missing_postgres_url(),
        ),
        ("redis", lambda: smoke_redis(redis_url)),
        ("chroma", lambda: smoke_chroma(settings.chroma_persist_directory)),
    )

    results: dict[str, dict[str, Any]] = {}
    for name, check in checks:
        try:
            results[name] = check()
        except Exception as error:  # noqa: BLE001 - each probe must report independently
            results[name] = {"ok": False, "error": _safe_error(error, secrets_to_redact)}

    passed = all(result.get("ok") is True for result in results.values())
    report = {
        "ok": passed,
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
