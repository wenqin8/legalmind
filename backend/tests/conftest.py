from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.db.base import Base
from app.db.session import Database
from app.llm.fake import FakeLLMClient
from app.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        log_level="DEBUG",
        cors_origins=["http://localhost:5173"],
        llm_backend="fake",
        jwt_secret_key="test-only-secret-at-least-32-characters-long",
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        embedding_backend="fake",
        chroma_persist_directory=tmp_path / "chroma",
    )


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient(response="deterministic test response", chunk_size=5)


@pytest.fixture
def app(settings: Settings, fake_llm: FakeLLMClient) -> Iterator[FastAPI]:
    database = Database(settings.database_url.get_secret_value())
    Base.metadata.create_all(database.engine)
    application = create_app(settings, llm_client=fake_llm, database=database)
    try:
        yield application
    finally:
        database.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as test_client:
        yield test_client
