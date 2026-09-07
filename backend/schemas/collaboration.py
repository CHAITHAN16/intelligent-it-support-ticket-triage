from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import TicketStatus


class CommentCreate(BaseModel):
    author_id: int | None = Field(default=None, gt=0)
    body: str = Field(..., max_length=5000)

    @field_validator("body")
    @classmethod
    def trim_and_reject_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    body: str
    created_at: datetime
    updated_at: datetime


class TicketStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    old_status: TicketStatus | None
    new_status: TicketStatus
    changed_by_id: int | None
    changed_at: datetime
    note: str | None
