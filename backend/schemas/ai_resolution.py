from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIResolutionMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def reject_empty_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be empty")
        return value


class AIResolutionConfirmRequest(BaseModel):
    confirmed: Literal[True]


class AIResolutionMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    speaker: str
    body: str
    created_at: datetime


class AIResolutionContextResponse(BaseModel):
    issue_summary: str
    start_time: str | None
    affected_devices_users: str | None
    affected_service: str | None
    exact_error: str | None
    known_troubleshooting_steps: list[str]
    missing_information: list[str]
    next_recommended_question: str


class AIResolutionResponse(BaseModel):
    mode: Literal["BASIC", "GUIDED"]
    status: str
    eligible: bool
    eligibility_reason: str | None
    escalation_reason: str | None
    classification_confidence: float | None
    knowledge_match_confidence: float | None
    assigned_team_name: str | None
    messages: list[AIResolutionMessageResponse]
    basic_context: AIResolutionContextResponse | None = None
