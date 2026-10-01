"""Idempotent bootstrap for the dedicated deployment database and vector volume."""
import subprocess
import sys
from app.core.config import Settings
from scripts import import_legal_data, import_verified_laws, index_legal_data


def main():
    settings = Settings()
    if not settings.database_url.get_secret_value().startswith('postgresql+psycopg://'):
        raise ValueError('Deployment bootstrap requires its dedicated PostgreSQL database')
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], check=True)
    for step in (import_legal_data.main, import_verified_laws.main, index_legal_data.main):
        if step() != 0: return 1
    return 0


if __name__ == '__main__': raise SystemExit(main())
