import logging
from uuid import UUID

import httpx
import jwt
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import User

pytestmark = pytest.mark.anyio

PASSWORD = "correct horse battery staple"


async def _register(
    client: httpx.AsyncClient,
    *,
    username: str = "Demo_User",
    email: str = "demo@example.com",
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": PASSWORD},
    )


async def _login(
    client: httpx.AsyncClient,
    *,
    login: str = "demo_user",
    password: str = PASSWORD,
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/login",
        json={"login": login, "password": password},
    )


async def test_register_hashes_password_and_normalizes_identity(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    response = await _register(
        client,
        username="  Ｄemo_User  ",
        email="Demo@Example.COM",
    )

    assert response.status_code == 201
    assert response.json()["data"]["username"] == "Demo_User"
    assert response.json()["data"]["email"] == "demo@example.com"
    assert "password" not in response.text

    with app.state.database.session() as session:
        user = session.scalar(select(User))
        assert user is not None
        assert user.username_normalized == "demo_user"
        assert user.email_normalized == "demo@example.com"
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2")


async def test_normalized_username_and_email_are_unique(
    client: httpx.AsyncClient,
) -> None:
    assert (await _register(client)).status_code == 201

    duplicate_username = await _register(
        client,
        username="ＤＥＭＯ＿ＵＳＥＲ",
        email="other@example.com",
    )
    duplicate_email = await _register(
        client,
        username="other_user",
        email="DEMO@EXAMPLE.COM",
    )

    assert duplicate_username.status_code == 409
    assert duplicate_username.json()["error"]["code"] == "ACCOUNT_ALREADY_EXISTS"
    assert duplicate_email.status_code == 409
    assert duplicate_email.json()["error"]["code"] == "ACCOUNT_ALREADY_EXISTS"


async def test_login_returns_strict_jwt_and_me_requires_it(
    client: httpx.AsyncClient,
    settings: Settings,
) -> None:
    register_response = await _register(client)
    user_id = register_response.json()["data"]["id"]
    login_response = await _login(client, login="DEMO_USER")

    assert login_response.status_code == 200
    token_data = login_response.json()["data"]
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] == 3600
    assert token_data["user"]["id"] == user_id

    claims = jwt.decode(
        token_data["access_token"],
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert claims["sub"] == user_id
    assert claims["typ"] == "access"
    assert all(name in claims for name in ("iat", "exp", "iss", "aud", "jti"))

    unauthenticated = await client.get("/api/v1/auth/me")
    authenticated = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["www-authenticate"] == "Bearer"
    assert authenticated.status_code == 200
    assert authenticated.json()["data"]["id"] == user_id


async def test_unknown_account_and_wrong_password_share_safe_error(
    client: httpx.AsyncClient,
) -> None:
    assert (await _register(client)).status_code == 201

    wrong_password = await _login(client, password="definitely wrong")
    unknown_account = await _login(client, login="nobody@example.com")

    assert wrong_password.status_code == unknown_account.status_code == 401
    assert wrong_password.json()["error"] == unknown_account.json()["error"]
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_tampered_token_and_inactive_user_are_rejected(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    register_response = await _register(client)
    user_id = register_response.json()["data"]["id"]
    token = (await _login(client)).json()["data"]["access_token"]

    tampered = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}x"},
    )
    assert tampered.status_code == 401
    assert tampered.headers["www-authenticate"] == "Bearer"

    with app.state.database.session() as session:
        user = session.get(User, UUID(user_id))
        assert user is not None
        user.is_active = False
        session.commit()

    inactive = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert inactive.status_code == 401
    assert inactive.headers["www-authenticate"] == "Bearer"


async def test_auth_logs_do_not_contain_password_or_token(
    client: httpx.AsyncClient,
    caplog,
) -> None:
    caplog.set_level(logging.INFO)
    assert (await _register(client)).status_code == 201
    login_response = await _login(client)
    token = login_response.json()["data"]["access_token"]
    assert login_response.status_code == 200

    _ = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert PASSWORD not in caplog.text
    assert token not in caplog.text


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "email": "demo@example.com", "password": PASSWORD},
        {"username": "demo", "email": "not-an-email", "password": PASSWORD},
        {"username": "demo", "email": "demo@example.com", "password": "short"},
        {
            "username": "demo",
            "email": "demo@example.com",
            "password": PASSWORD,
            "role": "admin",
        },
    ],
)
async def test_registration_rejects_invalid_or_extra_fields(
    client: httpx.AsyncClient,
    payload: dict[str, str],
) -> None:
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
