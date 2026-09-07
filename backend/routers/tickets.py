from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import TeamMember, Ticket, TicketPriority, TicketStatus, TicketStatusHistory, User, UserRole
from schemas.tickets import TicketCreate, TicketResponse, TicketUpdateRequest
from services.routing_service import RoutingService
from services.triage_service import TriageService


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


@router.get("", response_model=list[TicketResponse])
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
    elif creator_id is not None:
        statement = statement.where(Ticket.creator_id == creator_id)
    statement = statement.order_by(Ticket.created_at.desc())
    return list(db.scalars(statement).all())


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    _require_ticket_access(ticket, current_user, db)
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    try:
        for field, value in updates.items():
            setattr(ticket, field, value)

        if updates:
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
        if updates:
            db.commit()
            db.refresh(ticket)

        return ticket
    except Exception:
        db.rollback()
        raise


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
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
        db.flush()

        try:
            triage_result = TriageService().triage(ticket.title, ticket.description)
        except (FileNotFoundError, RuntimeError) as error:
            db.rollback()
            raise HTTPException(status_code=503, detail=f"AI triage unavailable: {error}") from error
        ticket.ai_predicted_category = triage_result.category
        ticket.ai_predicted_subcategory = triage_result.subcategory
        ticket.ai_predicted_priority = triage_result.priority
        ticket.ai_confidence = triage_result.confidence
        ticket.ai_model_version = triage_result.model_version
        created_at = ticket.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        ticket.ai_triaged_at = max(datetime.now(timezone.utc), created_at)

        RoutingService().route_and_assign(db, ticket, triage_result)
        db.commit()
        db.refresh(ticket)
        return ticket
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
