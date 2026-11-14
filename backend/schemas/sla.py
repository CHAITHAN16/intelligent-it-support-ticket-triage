from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models import TicketPriority


class SLATargetUpdate(BaseModel):
    response_minutes: int = Field(gt=0, le=525600)
    resolution_minutes: int = Field(gt=0, le=1051200)


class SLATargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    priority: TicketPriority
    response_minutes: int
    resolution_minutes: int
    updated_at: datetime


SLAState = Literal["ON_TRACK", "APPROACHING", "BREACHED", "MET", "NOT_APPLICABLE"]


class SLATeamMembershipResponse(BaseModel):
    team_id: int
    team_name: str


class EligibleAgentResponse(BaseModel):
    id: int
    name: str
    memberships: list[SLATeamMembershipResponse]


class SLAClockResponse(BaseModel):
    target_minutes: int
    deadline: datetime
    completed_at: datetime | None
    state: SLAState
    remaining_seconds: int | None
    overdue_seconds: int | None
    actively_overdue: bool


class TicketSLAResponse(BaseModel):
    ticket_id: int
    priority: TicketPriority
    status: str
    team_id: int | None
    created_at: datetime
    response: SLAClockResponse
    resolution: SLAClockResponse
    actively_overdue: bool


class SLAPriorityCounts(BaseModel):
    priority: TicketPriority
    tickets: int
    approaching_response: int
    approaching_resolution: int
    breached_response: int
    breached_resolution: int
    actively_overdue: int


class SLAOverviewResponse(BaseModel):
    generated_at: datetime
    approaching_within_minutes: int
    total_tickets: int
    priority_counts: list[SLAPriorityCounts]
    approaching_response: list[TicketSLAResponse]
    approaching_resolution: list[TicketSLAResponse]
    breached_response: list[TicketSLAResponse]
    breached_resolution: list[TicketSLAResponse]
