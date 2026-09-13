"""Run Week 2 migrations/imports in a random local PostgreSQL schema and remove it."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import BACKEND_DIR, Settings
from app.db.models import Case
from app.db.session import Database
from app.rag.importer import import_cases, load_case_records

CASES_PATH = BACKEND_DIR / "data" / "demo" / "cases.jsonl"


def _safe_local_postgres_url(raw_url: str) -> URL:
    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("PostgreSQL smoke URL is not PostgreSQL")
    if url.host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Week 2 verification only permits a loopback PostgreSQL host")
    return url.set(drivername="postgresql+psycopg")


@contextmanager
def _alembic_url(url: str):
    previous = os.environ.get("ALEMBIC_DATABASE_URL")
    os.environ["ALEMBIC_DATABASE_URL"] = url
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("ALEMBIC_DATABASE_URL", None)
        else:
            os.environ["ALEMBIC_DATABASE_URL"] = previous


def main() -> int:
    settings = Settings()
    if settings.postgres_smoke_url is None:
        raise SystemExit("LEGALMIND_POSTGRES_SMOKE_URL is not configured")
    admin_url = _safe_local_postgres_url(
        settings.postgres_smoke_url.get_secret_value()
    )
    schema_name = f"legalmind_m2_{uuid4().hex}"
    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    database: Database | None = None
    created = False
    result: dict[str, object] = {}
    try:
        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema_name))
        created = True
        schema_url = admin_url.update_query_dict(
            {"options": f"-csearch_path={schema_name}"}
        ).render_as_string(hide_password=False)
        alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
        alembic_config.set_main_option(
            "script_location", str(BACKEND_DIR / "migrations")
        )
        with _alembic_url(schema_url):
            command.upgrade(alembic_config, "head")

        database = Database(schema_url)
        records = load_case_records(CASES_PATH)
        first = import_cases(database, records)
        second = import_cases(database, records)
        columns = {
            column["name"]: column["type"]
            for column in inspect(database.engine).get_columns("cases")
        }
        with database.session() as session:
            case_count = session.scalar(select(func.count()).select_from(Case))
        result = {
            "migration_head": "20260913_0002",
            "tables_present": sorted(
                set(inspect(database.engine).get_table_names())
                & {"users", "conversations", "cases", "legal_provisions", "knowledge_chunks"}
            ),
            "case_count": case_count,
            "first_import": first.model_dump(),
            "second_import": second.model_dump(),
            "law_references_type": columns["law_references"].__class__.__name__,
        }
    finally:
        if database is not None:
            database.dispose()
        if created:
            with admin_engine.begin() as connection:
                connection.execute(DropSchema(schema_name, cascade=True, if_exists=True))
                remaining = connection.scalar(
                    text(
                        "SELECT count(1) FROM information_schema.schemata "
                        "WHERE schema_name = :schema_name"
                    ),
                    {"schema_name": schema_name},
                )
            result["schema_removed"] = remaining == 0
        admin_engine.dispose()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    checks = (
        result.get("case_count") == 16,
        result.get("first_import") == {"received": 16, "created": 16, "skipped": 0},
        result.get("second_import") == {"received": 16, "created": 0, "skipped": 16},
        result.get("law_references_type") == "JSONB",
        result.get("schema_removed") is True,
    )
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
