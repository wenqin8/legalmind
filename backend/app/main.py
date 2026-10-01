"""FastAPI application factory and ASGI entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.constants import API_V1_PREFIX, REQUEST_ID_HEADER
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, UnhandledExceptionMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import Database
from app.llm.base import LLMClient
from app.llm.factory import create_llm_client
from app.rag.embeddings import EmbeddingClient, create_embedding_client
from app.rag.retriever import HybridCaseRetriever
from app.rag.vector_store import ChromaVectorStore
from app.services.session_store import RedisSessionStore, SessionStore


def create_app(
    settings: Settings | None = None,
    *,
    llm_client: LLMClient | None = None,
    database: Database | None = None,
    embedding_client: EmbeddingClient | None = None,
    vector_store: ChromaVectorStore | None = None,
    case_retriever: HybridCaseRetriever | None = None,
    session_store: SessionStore | None = None,
) -> FastAPI:
    """Build an isolated application instance for runtime or tests."""

    resolved_settings = settings or get_settings()
    resolved_session_store = session_store or RedisSessionStore(resolved_settings.redis_url.get_secret_value())
    configure_logging(resolved_settings.log_level)
    resolved_llm_client = llm_client or create_llm_client(resolved_settings)
    resolved_database = database or Database(
        resolved_settings.database_url.get_secret_value()
    )
    resolved_embedding = embedding_client or create_embedding_client(resolved_settings)
    resolved_vector_store = vector_store or ChromaVectorStore(
        resolved_settings.chroma_persist_directory,
        resolved_settings.chroma_collection_name,
        resolved_embedding,
    )
    resolved_case_retriever = case_retriever or HybridCaseRetriever(
        resolved_database,
        resolved_vector_store,
        resolved_embedding,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            try:
                await resolved_llm_client.aclose()
            finally:
                try:
                    await resolved_session_store.aclose()
                finally:
                    resolved_database.dispose()

    expose_docs = resolved_settings.environment != "production"
    application = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        # Client responses never expose tracebacks, even in local development.
        debug=False,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.llm_client = resolved_llm_client
    application.state.database = resolved_database
    application.state.embedding_client = resolved_embedding
    application.state.vector_store = resolved_vector_store
    application.state.case_retriever = resolved_case_retriever
    application.state.session_store = resolved_session_store

    register_exception_handlers(application)
    application.add_middleware(UnhandledExceptionMiddleware)
    application.add_middleware(RateLimitMiddleware, auth_limit=resolved_settings.auth_rate_limit_per_minute,
                               business_limit=resolved_settings.business_rate_limit_per_minute)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER, "Content-Disposition"],
    )
    application.add_middleware(RequestContextMiddleware)
    application.include_router(api_router, prefix=API_V1_PREFIX)
    return application


app = create_app()
