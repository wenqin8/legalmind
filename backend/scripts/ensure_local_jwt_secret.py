"""Create a strong local JWT secret without printing it.

The generated value is written only to the ignored backend/.env file. Running
the script again is safe: an existing secret of at least 32 characters is kept.
"""

from __future__ import annotations

import os
import re
import secrets
import tempfile
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"
SETTING_NAME = "LEGALMIND_JWT_SECRET_KEY"
SETTING_PATTERN = re.compile(
    rf"^(?P<prefix>\s*{SETTING_NAME}\s*=\s*)(?P<value>.*)$",
    flags=re.MULTILINE,
)


def _unquote(value: str) -> str:
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        return normalized[1:-1]
    return normalized


def ensure_secret() -> str:
    if not ENV_PATH.is_file():
        raise SystemExit("backend/.env is missing; copy .env.example first")

    content = ENV_PATH.read_text(encoding="utf-8")
    match = SETTING_PATTERN.search(content)
    if match is not None and len(_unquote(match.group("value"))) >= 32:
        return "already configured"

    generated = secrets.token_urlsafe(48)
    if match is None:
        separator = "" if not content or content.endswith(("\n", "\r")) else os.linesep
        updated = f"{content}{separator}{SETTING_NAME}={generated}{os.linesep}"
    else:
        updated = SETTING_PATTERN.sub(
            lambda found: f"{found.group('prefix')}{generated}",
            content,
            count=1,
        )

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=ENV_PATH.parent,
            prefix=".env.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(updated)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, ENV_PATH)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return "configured"


if __name__ == "__main__":
    print(f"Local JWT secret: {ensure_secret()}")
