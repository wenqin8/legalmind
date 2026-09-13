"""Configure local PostgreSQL and Redis smoke-test secrets without printing them."""

from __future__ import annotations

import os
import re
import secrets
import tempfile
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"


def _unquote(value: str) -> str:
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        return normalized[1:-1]
    return normalized


def _read_setting(content: str, name: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*=\s*(?P<value>.*)$", re.MULTILINE)
    match = pattern.search(content)
    if match is None:
        return None
    value = _unquote(match.group("value"))
    return value or None


def _set_setting(content: str, name: str, value: str) -> str:
    pattern = re.compile(
        rf"^(?P<prefix>\s*{re.escape(name)}\s*=\s*).*$",
        re.MULTILINE,
    )
    if pattern.search(content):
        return pattern.sub(lambda match: f"{match.group('prefix')}{value}", content, count=1)
    separator = "" if not content or content.endswith(("\n", "\r")) else os.linesep
    return f"{content}{separator}{name}={value}{os.linesep}"


def ensure_settings(env_path: Path = ENV_PATH) -> str:
    if not env_path.is_file():
        raise SystemExit("backend/.env is missing; copy .env.example first")

    original = env_path.read_text(encoding="utf-8")
    postgres_password = _read_setting(original, "LEGALMIND_POSTGRES_PASSWORD")
    redis_password = _read_setting(original, "LEGALMIND_REDIS_PASSWORD")
    changed = False

    if postgres_password is None:
        postgres_password = secrets.token_urlsafe(32)
        changed = True
    if redis_password is None:
        redis_password = secrets.token_urlsafe(32)
        changed = True

    desired = {
        "LEGALMIND_POSTGRES_PASSWORD": postgres_password,
        "LEGALMIND_POSTGRES_SMOKE_URL": (
            f"postgresql://legalmind:{postgres_password}@127.0.0.1:5432/legalmind_smoke"
        ),
        "LEGALMIND_REDIS_PASSWORD": redis_password,
        "LEGALMIND_REDIS_URL": f"redis://:{redis_password}@127.0.0.1:6379/0",
        "LEGALMIND_CHROMA_PERSIST_DIRECTORY": "./data/chroma",
    }

    updated = original
    for name, value in desired.items():
        if _read_setting(updated, name) != value:
            updated = _set_setting(updated, name, value)
            changed = True

    if not changed:
        return "already configured"

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=env_path.parent,
            prefix=".env.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(updated)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, env_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return "configured"


if __name__ == "__main__":
    print(f"Local infrastructure settings: {ensure_settings()}")
