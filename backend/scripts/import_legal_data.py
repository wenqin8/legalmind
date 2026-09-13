"""Import validated legal source records into the configured relational database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import BACKEND_DIR, Settings
from app.db.session import Database
from app.rag.importer import (
    DataImportError,
    import_cases,
    import_legal_provisions,
    load_case_records,
    load_legal_provision_records,
)

DEFAULT_CASES_PATH = BACKEND_DIR / "data" / "demo" / "cases.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--cases", type=Path)
    sources.add_argument("--legal-provisions", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    database = Database(settings.database_url.get_secret_value())
    try:
        if args.legal_provisions is not None:
            summary = import_legal_provisions(
                database,
                load_legal_provision_records(args.legal_provisions.resolve()),
            )
            key = "legal_provisions"
        else:
            path = (args.cases or DEFAULT_CASES_PATH).resolve()
            summary = import_cases(database, load_case_records(path))
            key = "cases"
    except (OSError, DataImportError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        database.dispose()

    print(
        json.dumps(
            {"ok": True, key: summary.model_dump()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
