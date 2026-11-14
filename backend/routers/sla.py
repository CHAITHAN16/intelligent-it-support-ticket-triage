from datetime import datetime, timezone
from typing import Literal
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from auth import require_admin, require_agent
from database import get_db
from models import SLATarget, Team, TeamMember, Ticket, TicketPriority, TicketStatus, User, UserRole
from schemas.sla import (
    EligibleAgentResponse,
    SLAClockResponse,
    SLAOverviewResponse,
    SLAPriorityCounts,
    SLATargetResponse,
    SLATargetUpdate,
    TicketSLAResponse,
)
from services.sla_service import calculate_ticket_sla_clocks


router = APIRouter(prefix="/api/sla", tags=["sla"])
OverviewState = Literal["ON_TRACK", "APPROACHING", "BREACHED", "MET", "NOT_APPLICABLE"]
TERMINAL_STATUSES = (TicketStatus.RESOLVED, TicketStatus.CLOSED)


def _team_scope(team_id: int | None, user: User, db: Session):
    if team_id is not None:
        if db.get(Team, team_id) is None:
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        if user.role != UserRole.ADMIN and db.scalar(select(TeamMember.team_id).where(
            TeamMember.team_id == team_id, TeamMember.user_id == user.id,
        )) is None:
            raise HTTPException(status_code=403, detail="You are not a member of this team")
        return Ticket.assigned_team_id == team_id
    if user.role == UserRole.ADMIN:
        return None
    member_teams = select(TeamMember.team_id).where(TeamMember.user_id == user.id)
    return or_(Ticket.assigned_agent_id == user.id, Ticket.assigned_team_id.in_(member_teams))


def _ticket_projection(row) -> SimpleNamespace:
    return SimpleNamespace(
        id=row.id,
        title=row.title,
        priority=row.priority,
        status=row.status,
        assigned_team_id=row.assigned_team_id,
        created_at=row.created_at,
        first_response_at=row.first_response_at,
        resolved_at=row.resolved_at,
    )


def _sla_response(ticket: SimpleNamespace, target: SLATarget, now: datetime, approaching_within_minutes: int) -> TicketSLAResponse:
    result = calculate_ticket_sla_clocks(
        ticket, target, now, approaching_within_minutes=approaching_within_minutes,
    )
    return TicketSLAResponse(
        ticket_id=ticket.id,
        priority=ticket.priority,
        status=ticket.status.value,
        team_id=ticket.assigned_team_id,
        created_at=ticket.created_at,
        response=SLAClockResponse(**result.response.__dict__),
        resolution=SLAClockResponse(**result.resolution.__dict__),
        actively_overdue=result.actively_overdue,
    )


def _state_matches(item: TicketSLAResponse, state: OverviewState | None) -> bool:
    return state is None or item.response.state == state or item.resolution.state == state


def _sla_rows_statement():
    # Select only operational ticket fields; employee descriptions and AI data are never loaded.
    return select(
        Ticket.id.label("id"),
        Ticket.title.label("title"),
        Ticket.priority.label("priority"),
        Ticket.status.label("status"),
        Ticket.assigned_team_id.label("assigned_team_id"),
        Ticket.created_at.label("created_at"),
        Ticket.first_response_at.label("first_response_at"),
        Ticket.resolved_at.label("resolved_at"),
        SLATarget.response_minutes.label("response_minutes"),
        SLATarget.resolution_minutes.label("resolution_minutes"),
    ).join(SLATarget, SLATarget.priority == Ticket.priority)


@router.get("/targets", response_model=list[SLATargetResponse])
def list_sla_targets(current_user: User = Depends(require_agent), db: Session = Depends(get_db)):
    del current_user
    return list(db.scalars(select(SLATarget).order_by(SLATarget.priority)).all())


@router.put("/targets/{priority}", response_model=SLATargetResponse)
def update_sla_target(
    priority: TicketPriority,
    payload: SLATargetUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del current_user
    if payload.resolution_minutes < payload.response_minutes:
        raise HTTPException(status_code=422, detail="Resolution target must be at least the response target")
    target = db.get(SLATarget, priority)
    if target is None:
        target = SLATarget(priority=priority, **payload.model_dump())
        db.add(target)
    else:
        target.response_minutes = payload.response_minutes
        target.resolution_minutes = payload.resolution_minutes
    target.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(target)
    return target


@router.get("/tickets/{ticket_id}", response_model=TicketSLAResponse)
def get_ticket_sla(
    ticket_id: int,
    team_id: int | None = Query(default=None, ge=1),
    priority: TicketPriority | None = None,
    state: OverviewState | None = None,
    approaching_within_minutes: int = Query(default=60, ge=1, le=10080),
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db),
):
    scope = _team_scope(team_id, current_user, db)
    statement = _sla_rows_statement().where(Ticket.id == ticket_id)
    if scope is not None:
        statement = statement.where(scope)
    if priority is not None:
        statement = statement.where(Ticket.priority == priority)
    row = db.execute(statement).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    target = SLATarget(
        priority=row.priority,
        response_minutes=row.response_minutes,
        resolution_minutes=row.resolution_minutes,
    )
    now = datetime.now(timezone.utc)
    result = _sla_response(_ticket_projection(row), target, now, approaching_within_minutes)
    if state is not None and not _state_matches(result, state):
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return result


@router.get("/overview", response_model=SLAOverviewResponse)
def get_sla_overview(
    team_id: int | None = Query(default=None, ge=1),
    priority: TicketPriority | None = None,
    state: OverviewState | None = None,
    approaching_within_minutes: int = Query(default=60, ge=1, le=10080),
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db),
):
    scope = _team_scope(team_id, current_user, db)
    statement = _sla_rows_statement()
    if scope is not None:
        statement = statement.where(scope)
    if priority is not None:
        statement = statement.where(Ticket.priority == priority)
    rows = db.execute(statement.order_by(Ticket.created_at.desc(), Ticket.id.desc())).all()
    now = datetime.now(timezone.utc)
    results: list[TicketSLAResponse] = []
    for row in rows:
        target = SLATarget(
            priority=row.priority,
            response_minutes=row.response_minutes,
            resolution_minutes=row.resolution_minutes,
        )
        item = _sla_response(_ticket_projection(row), target, now, approaching_within_minutes)
        if _state_matches(item, state):
            results.append(item)

    priority_counts: list[SLAPriorityCounts] = []
    for ticket_priority in TicketPriority:
        priority_items = [item for item in results if item.priority == ticket_priority]
        priority_counts.append(SLAPriorityCounts(
            priority=ticket_priority,
            tickets=len(priority_items),
            approaching_response=sum(item.response.state == "APPROACHING" for item in priority_items),
            approaching_resolution=sum(item.resolution.state == "APPROACHING" for item in priority_items),
            breached_response=sum(item.response.state == "BREACHED" for item in priority_items),
            breached_resolution=sum(item.resolution.state == "BREACHED" for item in priority_items),
            actively_overdue=sum(item.actively_overdue for item in priority_items),
        ))

    active = [item for item in results if item.status not in {value.value for value in TERMINAL_STATUSES}]
    response_approaching = sorted(
        (item for item in active if item.response.state == "APPROACHING"),
        key=lambda item: item.response.deadline,
    )
    resolution_approaching = sorted(
        (item for item in active if item.resolution.state == "APPROACHING"),
        key=lambda item: item.resolution.deadline,
    )
    response_breached = sorted(
        (item for item in results if item.response.state == "BREACHED"),
        key=lambda item: item.response.overdue_seconds or 0,
        reverse=True,
    )
    resolution_breached = sorted(
        (item for item in results if item.resolution.state == "BREACHED"),
        key=lambda item: item.resolution.overdue_seconds or 0,
        reverse=True,
    )
    return SLAOverviewResponse(
        generated_at=now,
        approaching_within_minutes=approaching_within_minutes,
        total_tickets=len(results),
        priority_counts=priority_counts,
        approaching_response=response_approaching,
        approaching_resolution=resolution_approaching,
        breached_response=response_breached,
        breached_resolution=resolution_breached,
    )
