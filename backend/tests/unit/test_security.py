from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.errors import AuthenticationUnavailableError
from app.core.security import create_access_token, decode_access_token


def _settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        llm_backend="fake",
        jwt_secret_key="test-only-secret-at-least-32-characters-long",
        **overrides,
    )


def _claims(settings: Settings, **overrides: object) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    claims: dict[str, object] = {
        "sub": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": str(uuid4()),
        "typ": "access",
    }
    claims.update(overrides)
    return claims


def test_access_token_contains_only_identity_and_required_control_claims() -> None:
    settings = _settings()
    user_id = uuid4()

    token, expires_in = create_access_token(user_id, settings)
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )

    assert expires_in == 3600
    assert decode_access_token(token, settings) == user_id
    assert set(claims) == {"sub", "iat", "exp", "iss", "aud", "jti", "typ"}
    assert not {"email", "username", "password", "password_hash"}.intersection(claims)


@pytest.mark.parametrize(
    "claim_overrides",
    [
        {"exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        {"iss": "wrong-issuer"},
        {"aud": "wrong-audience"},
        {"sub": "not-a-uuid"},
        {"jti": "not-a-uuid"},
        {"typ": "refresh"},
    ],
)
def test_invalid_claims_are_rejected(claim_overrides: dict[str, object]) -> None:
    settings = _settings()
    token = jwt.encode(
        _claims(settings, **claim_overrides),
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )

    assert decode_access_token(token, settings) is None


def test_unsigned_and_malformed_tokens_are_rejected() -> None:
    settings = _settings()
    unsigned = jwt.encode(_claims(settings), key="", algorithm="none")

    assert decode_access_token(unsigned, settings) is None
    assert decode_access_token("not-a-token", settings) is None


@pytest.mark.parametrize('nested_part', ['header', 'payload'])
def test_deeply_nested_token_is_rejected_without_uncaught_recursion(nested_part):
    settings = _settings()
    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b'=')
    nested = b'[' * 2000 + b']' * 2000
    header = encode(nested if nested_part == 'header' else b'{"alg":"HS256","typ":"JWT"}')
    payload = encode(nested if nested_part == 'payload' else b'{}')
    unsigned = header + b'.' + payload
    signature = encode(hmac.new(settings.jwt_secret_key.get_secret_value().encode(), unsigned, hashlib.sha256).digest())
    assert decode_access_token((unsigned + b'.' + signature).decode(), settings) is None


def test_missing_or_short_secret_fails_closed() -> None:
    user_id = uuid4()
    for secret in (None, "too-short"):
        settings = Settings(
            _env_file=None,
            environment="test",
            llm_backend="fake",
            jwt_secret_key=secret,
        )
        with pytest.raises(AuthenticationUnavailableError):
            create_access_token(user_id, settings)
