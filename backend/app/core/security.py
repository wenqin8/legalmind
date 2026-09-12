"""Password and access-token primitives."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.errors import AuthenticationUnavailableError

JWT_ALGORITHM = "HS256"
PASSWORD_HASHER = PasswordHash.recommended()
# Generated once per process so unknown accounts still perform an Argon2 verify.
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("dummy-password-never-used-for-login")


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password, password_hash)
    except (TypeError, ValueError):
        return False


def _secret(settings: Settings) -> str:
    if settings.jwt_secret_key is None:
        raise AuthenticationUnavailableError()
    secret = settings.jwt_secret_key.get_secret_value()
    if len(secret) < 32:
        raise AuthenticationUnavailableError()
    return secret


def create_access_token(user_id: UUID, settings: Settings) -> tuple[str, int]:
    expires_in = settings.access_token_expire_minutes * 60
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=expires_in),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": str(uuid4()),
        "typ": "access",
    }
    token = jwt.encode(
        payload,
        _secret(settings),
        algorithm=JWT_ALGORITHM,
        headers={"typ": "JWT"},
    )
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> UUID | None:
    try:
        payload = jwt.decode(
            token,
            _secret(settings),
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": ["sub", "iat", "exp", "iss", "aud", "jti", "typ"]
            },
        )
        if payload.get("typ") != "access":
            return None
        jti = payload.get("jti")
        if not isinstance(jti, str):
            return None
        UUID(jti)
        subject = payload.get("sub")
        if not isinstance(subject, str):
            return None
        return UUID(subject)
    except (InvalidTokenError, ValueError, TypeError):
        return None
