"""Manually activate reviewed official statute snapshots, without touching case indexes."""

import argparse
import json
from pathlib import Path

from app.core.config import BACKEND_DIR, Settings
from app.db.session import Database
from app.rag.legal_catalog import import_catalog, load_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=BACKEND_DIR / "data/legal/verified_provisions.jsonl")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        records = load_catalog(args.catalog)
        if args.check_only:
            print(json.dumps({"valid": True, "records": len(records)}))
            return 0
        database = Database(Settings().database_url.get_secret_value())
        try:
            result = import_catalog(database, records)
        finally:
            database.dispose()
        print(json.dumps({"ok": True, **result}))
        return 0
    except Exception as exc:
        # Never dump raw submitted records or connection strings.
        print(json.dumps({"ok": False, "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
