"""Short transactions; no SQL sessions span model/network requests."""

from uuid import UUID, uuid4
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from app.core.errors import DatabaseUnavailableError, ResourceNotFoundError
from app.db.models import Conversation, utc_now
from app.db.session import Database
from app.services.documents import PreparedDocument


def resolve_session(database: Database, user_id: UUID, requested: UUID | None) -> tuple[UUID, bool]:
    if requested is None:
        return uuid4(), True
    try:
        with database.session() as session:
            found = session.scalar(select(Conversation.id).where(Conversation.id == requested, Conversation.user_id == user_id))
            if found is None:
                raise ResourceNotFoundError()
            return found, False
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


def get_commit_marker(database: Database, user_id: UUID, session_id: UUID) -> UUID | None:
    try:
        with database.session() as session:
            row = session.scalar(select(Conversation).where(Conversation.id == session_id, Conversation.user_id == user_id))
            if row is None:
                raise ResourceNotFoundError()
            return row.history_commit_id
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


def save_completion(database: Database, user_id: UUID, session_id: UUID, is_new: bool, question: str, document: PreparedDocument | None, turn_id: UUID) -> None:
    try:
        with database.session() as session, session.begin():
            if is_new:
                session.add(Conversation(id=session_id, user_id=user_id, title=" ".join(question.split())[:24] or "新咨询", history_commit_id=turn_id))
            else:
                conversation = session.scalar(select(Conversation).where(Conversation.id == session_id, Conversation.user_id == user_id))
                if conversation is None:
                    raise ResourceNotFoundError()
                conversation.updated_at = utc_now()
                conversation.history_commit_id = turn_id
            if document:
                session.add(document.row(user_id))
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


def delete_session(database: Database, user_id: UUID, session_id: UUID) -> None:
    try:
        with database.session() as session, session.begin():
            conversation = session.scalar(select(Conversation).where(Conversation.id == session_id, Conversation.user_id == user_id))
            if conversation is None:
                raise ResourceNotFoundError()
            session.delete(conversation)
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


def list_sessions(database: Database, user_id: UUID, offset: int, limit: int) -> tuple[list[Conversation], int]:
    try:
        with database.session() as session:
            rows = list(session.scalars(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc(), Conversation.id.desc()).offset(offset).limit(limit)))
            total = session.scalar(select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)) or 0
            return rows, total
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc
