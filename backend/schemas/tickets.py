from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    creator_id: int

    @field_validator("title", "description")
    @classmethod
    def reject_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class TicketUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None

    @field_validator("title", "description")
    @classmethod
    def reject_empty_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be empty")
        return value


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: str | None
    subcategory: str | None
    priority: TicketPriority
    status: TicketStatus
    creator_id: int
    created_at: datetime
    updated_at: datetime
    ai_predicted_category: str | None
    ai_predicted_subcategory: str | None
    ai_predicted_priority: TicketPriority | None
    ai_confidence: float | None
    ai_model_version: str | None
    ai_triaged_at: datetime | None
