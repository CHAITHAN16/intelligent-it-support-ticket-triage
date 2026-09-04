from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from models import Ticket, TicketPriority, TicketStatus
from schemas.tickets import TicketCreate, TicketResponse


router = APIRouter(prefix="/api/tickets", tags=["tickets"])


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
