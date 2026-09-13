from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from scripts.ensure_local_infrastructure_secrets import ensure_settings
from scripts.smoke_infrastructure import _redaction_values, _safe_error, smoke_chroma


def test_infrastructure_secret_setup_is_idempotent(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("LEGALMIND_ENVIRONMENT=test\n", encoding="utf-8")

    assert ensure_settings(env_path) == "configured"
    first_content = env_path.read_text(encoding="utf-8")
    assert ensure_settings(env_path) == "already configured"
    assert env_path.read_text(encoding="utf-8") == first_content
    assert "LEGALMIND_POSTGRES_SMOKE_URL=postgresql://legalmind:" in first_content
    assert "LEGALMIND_REDIS_URL=redis://:" in first_content


def test_chroma_persistent_round_trip_cleans_probe_collection(tmp_path: Path) -> None:
    persist_directory = tmp_path / "chroma"
    result = smoke_chroma(persist_directory)

    assert result["ok"] is True
    assert result["heartbeat"] > 0
    client = chromadb.PersistentClient(
        path=str(persist_directory),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    assert client.list_collections() == []


def test_smoke_error_redacts_urls_and_embedded_passwords() -> None:
    postgres_url = "postgresql://user:postgres-secret@127.0.0.1:5432/legalmind"
    redis_url = "redis://:redis-secret@127.0.0.1:6379/0"
    error = RuntimeError(f"failed with {postgres_url}; password=redis-secret")

    message = _safe_error(error, _redaction_values(postgres_url, redis_url))

    assert "postgres-secret" not in message
    assert "redis-secret" not in message
    assert postgres_url not in message
