from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Ticket, TicketPriority, TicketStatus
from schemas.tickets import TicketCreate, TicketResponse, TicketUpdateRequest
from services.triage_service import TriageService


router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketResponse])
def list_tickets(db: Session = Depends(get_db)) -> list[Ticket]:
    statement = select(Ticket).order_by(Ticket.created_at.desc())
    return list(db.scalars(statement).all())


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: int, payload: TicketUpdateRequest, db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(ticket, field, value)

    if updates:
        ticket.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ticket)

    return ticket


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        creator_id=payload.creator_id,
        category=None,
        subcategory=None,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.NEW,
    )

    triage_result = TriageService().triage(ticket.title, ticket.description)
    ticket.ai_predicted_category = triage_result.category
    ticket.ai_predicted_subcategory = triage_result.subcategory
    ticket.ai_predicted_priority = triage_result.priority
    ticket.ai_confidence = triage_result.confidence
    ticket.ai_model_version = triage_result.model_version
    ticket.ai_triaged_at = datetime.now(timezone.utc)

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
