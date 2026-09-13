"""Version 1 route composition."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, cases, chat, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(cases.router, tags=["cases"])
