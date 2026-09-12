"""Registration and login operations."""

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import Settings
from app.core.errors import (
    AccountAlreadyExistsError,
    DatabaseUnavailableError,
    InvalidCredentialsError,
)
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.session import Database
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenData,
    UserData,
    normalize_identity,
)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def public_user(user: User) -> UserData:
    return UserData(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=_utc(user.created_at),
    )


def register_user(payload: RegisterRequest, database: Database) -> UserData:
    username_normalized = normalize_identity(payload.username)
    email = str(payload.email).strip().lower()
    email_normalized = normalize_identity(email)

    try:
        with database.session() as session:
            duplicate = session.scalar(
                select(User.id).where(
                    or_(
                        User.username_normalized == username_normalized,
                        User.email_normalized == email_normalized,
                    )
                )
            )
            if duplicate is not None:
                raise AccountAlreadyExistsError()

            user = User(
                username=payload.username,
                username_normalized=username_normalized,
                email=email,
                email_normalized=email_normalized,
                password_hash=hash_password(payload.password),
            )
            session.add(user)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise AccountAlreadyExistsError() from exc
            return public_user(user)
    except AccountAlreadyExistsError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


def login_user(
    payload: LoginRequest,
    database: Database,
    settings: Settings,
) -> TokenData:
    normalized_login = normalize_identity(payload.login)
    try:
        with database.session() as session:
            user = session.scalar(
                select(User).where(
                    or_(
                        User.username_normalized == normalized_login,
                        User.email_normalized == normalized_login,
                    )
                )
            )
            password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
            password_matches = verify_password(payload.password, password_hash)
            if user is None or not password_matches or not user.is_active:
                raise InvalidCredentialsError()

            token, expires_in = create_access_token(user.id, settings)
            return TokenData(
                access_token=token,
                expires_in=expires_in,
                user=public_user(user),
            )
    except (InvalidCredentialsError,):
        raise
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc
