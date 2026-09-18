from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_is_reversible_and_matches_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", database_url)
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert {
            "alembic_version",
            "users",
            "conversations",
            "cases",
            "legal_provisions",
            "knowledge_chunks",
            "generated_documents",
        }.issubset(
            inspector.get_table_names()
        )
        assert {
            index["name"] for index in inspector.get_indexes("conversations")
        } == {"ix_conversations_id_user_id"}
        assert {
            index["name"] for index in inspector.get_indexes("cases")
        } == {"ix_cases_domain_status"}
        assert "history_commit_id" in {column["name"] for column in inspector.get_columns("conversations")}
    finally:
        engine.dispose()

    command.check(config)
    command.downgrade(config, "base")
    engine = create_engine(database_url)
    try:
        assert inspect(engine).get_table_names() == ["alembic_version"]
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    command.check(config)
