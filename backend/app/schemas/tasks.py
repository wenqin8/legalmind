"""Bounded, message-grounded task state stored with each committed assistant turn."""

from typing import Literal
from uuid import UUID, uuid4
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskAction = Literal["confirm", "accept_changes", "reject_changes", "cancel", "restart"]
Domain = Literal["marriage_family", "labor_dispute", "traffic_accident", "contract_dispute"]


class GroundedValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(min_length=1, max_length=4000)
    source_turn_id: UUID
    quote: str = Field(min_length=1, max_length=4000)
    source: Literal["message", "parameters"] = "message"


class TaskState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: UUID = Field(default_factory=uuid4)
    revision: UUID = Field(default_factory=uuid4)
    kind: Literal["qa", "document"]
    phase: Literal["collecting", "conflict", "review", "completed", "cancelled"] = "collecting"
    document_type: Literal["civil_complaint", "civil_defense", "general_contract"] | None = None
    domain: Domain | None = None
    mode: Literal["event", "general"] = "event"
    fields: dict[str, GroundedValue] = Field(default_factory=dict, max_length=16)
    conflicts: dict[str, GroundedValue] = Field(default_factory=dict, max_length=16)
    missing_fields: list[str] = Field(default_factory=list, max_length=16)
    questions: list[str] = Field(default_factory=list, max_length=3)
    document_id: UUID | None = None
    requires_local_material: bool = False

    @model_validator(mode="after")
    def bounded_state(self):
        # Provenance remains available after its original message is trimmed.
        if len(json.dumps({k: v.value for k, v in self.fields.items()}, ensure_ascii=False).encode("utf-8")) > 20480:
            raise ValueError("Task parameters exceed 20KB")
        return self
