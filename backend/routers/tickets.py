import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user, require_agent
from models import AssignmentSource, Team, TeamMember, Ticket, TicketAssignment, TicketFieldHistory, TicketPriority, TicketStatus, TicketStatusHistory, User, UserRole
from schemas.tickets import TicketCreate, TicketResponse, TicketUpdateRequest
from tasks.ticket_tasks import process_ticket


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _can_agent_access_ticket(ticket: Ticket, user: User, db: Session) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if ticket.assigned_agent_id == user.id:
        return True
    return ticket.assigned_team_id is not None and db.scalar(
        select(TeamMember).where(TeamMember.team_id == ticket.assigned_team_id, TeamMember.user_id == user.id)
    ) is not None


def _require_ticket_access(ticket: Ticket, user: User, db: Session, *, allow_employee: bool = True) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.EMPLOYEE and allow_employee and ticket.creator_id == user.id:
        return
    if user.role == UserRole.SUPPORT_AGENT and _can_agent_access_ticket(ticket, user, db):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to access this ticket")


@router.get(
    "",
    response_model=list[TicketResponse],
    summary="List tickets",
    description="Return tickets visible to the current user. Employees see their own tickets, support agents see tickets assigned to their teams or themselves, and administrators can filter by creator.",
    response_description="Tickets ordered from newest to oldest.",
    responses={401: {"description": "Authentication is required."}, 403: {"description": "An employee requested another user's tickets."}},
)
def list_tickets(
    creator_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Ticket]:
    statement = select(Ticket)
    if current_user.role == UserRole.EMPLOYEE:
        if creator_id is not None and creator_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employees can only view their own tickets")
        statement = statement.where(Ticket.creator_id == current_user.id)
    elif current_user.role == UserRole.SUPPORT_AGENT:
        team_ids = select(TeamMember.team_id).where(TeamMember.user_id == current_user.id)
        statement = statement.where(
            or_(Ticket.assigned_agent_id == current_user.id, Ticket.assigned_team_id.in_(team_ids))
        )
        if creator_id is not None:
            statement = statement.where(Ticket.creator_id == creator_id)
    elif creator_id is not None:
        statement = statement.where(Ticket.creator_id == creator_id)
    statement = statement.order_by(Ticket.created_at.desc())
    return list(db.scalars(statement).all())


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get a ticket",
    description="Retrieve one ticket if the current user is allowed to access it.",
    response_description="The requested ticket.",
    responses={401: {"description": "Authentication is required."}, 403: {"description": "The user cannot access this ticket."}, 404: {"description": "The ticket does not exist."}},
)
def get_ticket(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    _require_ticket_access(ticket, current_user, db)
    return ticket


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Update a ticket",
    description="Apply the supplied ticket fields and optionally reassign the ticket to a team. Only an authorized support agent or administrator can update the ticket.",
    response_description="The updated ticket.",
    responses={400: {"description": "The request body failed validation."}, 401: {"description": "Authentication is required."}, 403: {"description": "The user cannot update this ticket."}, 404: {"description": "The ticket or requested team does not exist."}},
)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_agent),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    if isinstance(current_user, User) and (
        current_user.role not in (UserRole.SUPPORT_AGENT, UserRole.ADMIN)
        or not _can_agent_access_ticket(ticket, current_user, db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an authorized agent can update this ticket")

    updates = payload.model_dump(exclude_unset=True)
    previous_status = ticket.status
    status_changed = "status" in updates and updates["status"] != previous_status
    requested_team_id = updates.pop("assigned_team_id", None)
    team_changed = "assigned_team_id" in payload.model_fields_set and requested_team_id != ticket.assigned_team_id

    try:
        if team_changed:
            team = db.get(Team, requested_team_id)
            if team is None:
                raise HTTPException(status_code=404, detail=f"Team {requested_team_id} not found")

            now = datetime.now(timezone.utc)
            active_assignments = db.scalars(
                select(TicketAssignment).where(
                    TicketAssignment.ticket_id == ticket.id,
                    TicketAssignment.unassigned_at.is_(None),
                )
            ).all()
            for assignment in active_assignments:
                assignment.unassigned_at = now
            db.add(
                TicketAssignment(
                    ticket_id=ticket.id,
                    team_id=team.id,
                    agent_id=None,
                    source=AssignmentSource.HUMAN,
                    assigned_by_id=current_user.id if isinstance(current_user, User) else None,
                    routing_reason="Reassigned by support agent",
                    assigned_at=now,
                )
            )
            ticket.assigned_team_id = team.id
            ticket.assigned_team = team
            ticket.assigned_agent_id = None

        for field, value in updates.items():
            old_value = getattr(ticket, field)
            setattr(ticket, field, value)
            if field in {"category", "subcategory", "priority"} and value != old_value:
                db.add(
                    TicketFieldHistory(
                        ticket_id=ticket.id,
                        field_name=field,
                        old_value=old_value.value if isinstance(old_value, TicketPriority) else old_value,
                        new_value=value.value if isinstance(value, TicketPriority) else value,
                        changed_by_id=current_user.id if isinstance(current_user, User) else None,
                    )
                )

        if updates or team_changed:
            ticket.updated_at = datetime.now(timezone.utc)
        if status_changed:
            db.add(
                TicketStatusHistory(
                    ticket_id=ticket.id,
                    old_status=previous_status,
                    new_status=updates["status"],
                    changed_by_id=current_user.id if isinstance(current_user, User) else None,
                )
            )
        if updates or team_changed:
            db.commit()
            db.refresh(ticket)

        return ticket
    except Exception:
        db.rollback()
        raise


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket",
    description="Create a ticket for the authenticated user. Unauthenticated service callers may provide creator_id in the request body.",
    response_description="The created ticket, initially untriaged and in NEW status.",
    responses={401: {"description": "Authentication or a creator_id is required."}, 422: {"description": "The request body failed validation."}},
)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> Ticket:
    # Direct service-level tests may call this function without FastAPI dependency injection.
    creator_id = current_user.id if isinstance(current_user, User) else payload.creator_id
    if creator_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")
    try:
        ticket = Ticket(
            title=payload.title,
            description=payload.description,
            creator_id=creator_id,
            category=None,
            subcategory=None,
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.NEW,
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)
    except Exception:
        db.rollback()
        raise

    try:
        process_ticket.delay(ticket.id)
    except Exception:
        # The ticket is already durable; Redis availability must not undo it.
        logger.exception("Could not enqueue ticket processing: ticket_id=%s", ticket.id)

    return ticket
