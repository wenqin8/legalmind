import asyncio

import pytest

from app.core.config import Settings
from app.llm.fake import FakeLLMClient
from app.main import create_app


class ClosableFakeLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


def test_application_factory_is_repeatable() -> None:
    settings = Settings(_env_file=None, environment="test", llm_backend="fake")

    first = create_app(settings)
    second = create_app(settings)

    assert first is not second
    assert first.version == second.version == "0.1.0"


def test_day_five_public_and_authenticated_routes_are_mounted() -> None:
    settings = Settings(_env_file=None, environment="test", llm_backend="fake")
    app = create_app(settings)
    business_paths = {
        path for path in app.openapi()["paths"] if path.startswith("/api/v1")
    }

    assert business_paths == {
        "/api/v1/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/chat/send",
    }


def test_production_disables_interactive_docs() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        llm_backend="fake",
        jwt_secret_key="production-test-secret-at-least-32-characters",
    )
    app = create_app(settings)

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_debug_setting_never_exposes_fastapi_tracebacks() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        debug=True,
        llm_backend="fake",
    )
    app = create_app(settings)

    assert app.debug is False


def test_lifespan_closes_llm_client() -> None:
    async def scenario() -> None:
        settings = Settings(_env_file=None, environment="test", llm_backend="fake")
        llm_client = ClosableFakeLLMClient()
        app = create_app(settings, llm_client=llm_client)

        async with app.router.lifespan_context(app):
            assert not llm_client.closed

        assert llm_client.closed

    asyncio.run(scenario())


def test_lifespan_closes_llm_client_after_failure() -> None:
    async def scenario() -> None:
        settings = Settings(_env_file=None, environment="test", llm_backend="fake")
        llm_client = ClosableFakeLLMClient()
        app = create_app(settings, llm_client=llm_client)

        with pytest.raises(RuntimeError, match="startup scenario failed"):
            async with app.router.lifespan_context(app):
                raise RuntimeError("startup scenario failed")

        assert llm_client.closed

    asyncio.run(scenario())
