"""Registration, JWT login, and current-user endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_database,
    get_runtime_settings,
)
from app.core.config import Settings
from app.db.session import Database
from app.schemas.auth import LoginRequest, RegisterRequest, TokenData, UserData
from app.schemas.common import ApiSuccess
from app.services.auth import login_user, register_user

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=ApiSuccess[UserData],
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    request: Request,
    database: Annotated[Database, Depends(get_database)],
) -> ApiSuccess[UserData]:
    return ApiSuccess(
        data=register_user(payload, database),
        request_id=request.state.request_id,
    )


@router.post("/login", response_model=ApiSuccess[TokenData])
def login(
    payload: LoginRequest,
    request: Request,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> ApiSuccess[TokenData]:
    return ApiSuccess(
        data=login_user(payload, database, settings),
        request_id=request.state.request_id,
    )


@router.get("/me", response_model=ApiSuccess[UserData])
def get_me(
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ApiSuccess[UserData]:
    return ApiSuccess(
        data=UserData(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            created_at=current_user.created_at,
        ),
        request_id=request.state.request_id,
    )
