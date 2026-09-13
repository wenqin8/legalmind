"""Shared FastAPI dependencies for API routes."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.core.errors import AuthenticationRequiredError, DatabaseUnavailableError
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import Database
from app.llm.base import LLMClient
from app.rag.retriever import HybridCaseRetriever

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The minimum authenticated identity exposed to business routes."""

    id: UUID
    username: str
    email: str
    created_at: datetime


def get_llm_client(request: Request) -> LLMClient:
    """Resolve the application-scoped model adapter."""

    return request.app.state.llm_client


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_case_retriever(request: Request) -> HybridCaseRetriever:
    return request.app.state.case_retriever


def get_runtime_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthenticatedUser:
    """Validate a JWT and resolve an active user from the database."""

    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise AuthenticationRequiredError()

    settings = get_runtime_settings(request)
    user_id = decode_access_token(credentials.credentials, settings)
    if user_id is None:
        raise AuthenticationRequiredError()

    database = get_database(request)
    try:
        with database.session() as session:
            user = session.scalar(
                select(User).where(User.id == user_id, User.is_active.is_(True))
            )
            if user is None:
                raise AuthenticationRequiredError()
            created_at = user.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            current_user = AuthenticatedUser(
                id=user.id,
                username=user.username,
                email=user.email,
                created_at=created_at,
            )
    except AuthenticationRequiredError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc

    request.state.user_id = current_user.id
    return current_user
