from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Ticket, TicketPriority, TicketStatus
from schemas.tickets import TicketCreate, TicketResponse


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
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
