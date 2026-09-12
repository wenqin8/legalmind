"""Strict authentication request and response schemas."""

import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def normalize_display_username(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def normalize_identity(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = normalize_display_username(value)
        if not 3 <= len(normalized) <= 50:
            raise ValueError("Username must be between 3 and 50 characters")
        if any(unicodedata.category(character).startswith("C") for character in normalized):
            raise ValueError("Username contains unsupported characters")
        if "@" in normalized:
            raise ValueError("Username cannot contain an at sign")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        normalized = str(value).strip().lower()
        if len(normalize_identity(normalized)) > 254:
            raise ValueError("Normalized email is too long")
        return normalized


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("login")
    @classmethod
    def normalize_login(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).strip()
        if not normalized:
            raise ValueError("Login cannot be empty")
        return normalized


class UserData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    created_at: datetime


class TokenData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserData
