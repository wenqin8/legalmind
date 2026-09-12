"""Database engine and short-lived session factory."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, url: str) -> None:
        parsed_url = make_url(url)
        connect_args: dict[str, object] = {}
        if parsed_url.get_backend_name() == "sqlite":
            connect_args["check_same_thread"] = False
            if parsed_url.database and parsed_url.database != ":memory:":
                Path(parsed_url.database).expanduser().resolve().parent.mkdir(
                    parents=True, exist_ok=True
                )

        self.engine: Engine = create_engine(
            parsed_url,
            connect_args=connect_args,
            pool_pre_ping=parsed_url.get_backend_name() != "sqlite",
        )
        if parsed_url.get_backend_name() == "sqlite":
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        self._session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

    @staticmethod
    def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()
