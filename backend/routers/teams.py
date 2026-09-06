from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from database import get_db
from models import Team, Ticket, TicketPriority, TicketStatus
from schemas.teams import TeamResponse
from schemas.tickets import TicketResponse


router = APIRouter(prefix="/api/teams", tags=["teams"])
CategoryFilter = Literal["Network", "Security", "Software", "Other"]
SortOrder = Literal["newest", "oldest", "priority"]


@router.get("", response_model=list[TeamResponse])
def list_teams(db: Session = Depends(get_db)) -> list[Team]:
    statement = select(Team).order_by(Team.name.asc())
    return list(db.scalars(statement).all())


@router.get("/{team_id}/tickets", response_model=list[TicketResponse])
def list_team_tickets(
    team_id: int,
    status: TicketStatus | None = Query(default=None),
    priority: TicketPriority | None = Query(default=None),
    category: CategoryFilter | None = Query(default=None),
    sort: SortOrder = Query(default="newest"),
    db: Session = Depends(get_db),
) -> list[Ticket]:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

    statement = select(Ticket).where(Ticket.assigned_team_id == team_id)
    if status is not None:
        statement = statement.where(Ticket.status == status)
    if priority is not None:
        statement = statement.where(Ticket.priority == priority)
    if category is not None:
        statement = statement.where(Ticket.category == category)

    if sort == "oldest":
        statement = statement.order_by(Ticket.created_at.asc())
    elif sort == "priority":
        priority_rank = case(
            (Ticket.priority == TicketPriority.URGENT, 4),
            (Ticket.priority == TicketPriority.HIGH, 3),
            (Ticket.priority == TicketPriority.MEDIUM, 2),
            (Ticket.priority == TicketPriority.LOW, 1),
            else_=0,
        )
        statement = statement.order_by(priority_rank.desc(), Ticket.created_at.desc())
    else:
        statement = statement.order_by(Ticket.created_at.desc())

    return list(db.scalars(statement).all())
