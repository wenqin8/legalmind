"""Shared API response models."""

from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class ApiSuccess(BaseModel, Generic[DataT]):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: DataT
    request_id: UUID
