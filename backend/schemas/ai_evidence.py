from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models import TicketPriority


TicketCategory = Literal["Network", "Security", "Software", "Other"]


class TicketPredictionEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    predicted_category: str
    predicted_priority: TicketPriority
    category_model_version: str
    priority_model_version: str
    runtime_model_version: str
    category_probabilities: dict[str, float]
    priority_probabilities: dict[str, float]
    classification_confidence: float
    combined_confidence: float
    predicted_at: datetime


class TicketPredictionReviewCreate(BaseModel):
    prediction_evidence_id: int = Field(gt=0)
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_a_reviewed_field(self):
        if self.category is None and self.priority is None:
            raise ValueError("At least one of category or priority must be reviewed")
        return self


class TicketPredictionReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    prediction_evidence_id: int
    reviewer_id: int
    field_name: str
    predicted_value: str
    confirmed_value: str
    outcome: Literal["ACCEPTED", "OVERRIDDEN"]
    reviewed_at: datetime
    reason: str | None
