from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    creator_id: int | None = Field(default=None, gt=0)

    @field_validator("title", "description")
    @classmethod
    def reject_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class TicketUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, max_length=100)
    subcategory: str | None = Field(default=None, max_length=100)
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assigned_team_id: int | None = Field(default=None, gt=0)
    resolution_note: str | None = Field(default=None, max_length=5000)

    @field_validator("title", "description")
    @classmethod
    def reject_empty_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("category", "subcategory")
    @classmethod
    def reject_blank_classification(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("resolution_note")
    @classmethod
    def validate_resolution_note(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if value and len(value) < 10:
            raise ValueError("resolution note must contain at least 10 characters")
        return value or None


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
    assigned_team_id: int | None
    assigned_agent_id: int | None
    assigned_team_name: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
    ai_predicted_category: str | None
    ai_predicted_subcategory: str | None
    ai_predicted_priority: TicketPriority | None
    ai_confidence: float | None
    ai_classification_confidence: float | None
    ai_model_version: str | None
    ai_triaged_at: datetime | None
    routing_reason: str | None
    solution_status: str | None = None
    solution_confidence_level: str | None = None
    suggested_solution: str | None = None
    knowledge_article_id: int | None = None
    knowledge_article_title: str | None = None
    solution_confidence: float | None = None
    solution_source: str | None = None


class TicketAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    team_id: int | None
    agent_id: int | None
    source: str
    assigned_by_id: int | None
    routing_reason: str | None
    assigned_at: datetime
    unassigned_at: datetime | None
