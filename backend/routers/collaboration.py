from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Comment, Ticket, TicketStatusHistory, User
from schemas.collaboration import CommentCreate, CommentResponse, TicketStatusHistoryResponse


router = APIRouter(prefix="/api/tickets", tags=["ticket-collaboration"])


def _require_ticket(ticket_id: int, db: Session) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(ticket_id: int, payload: CommentCreate, db: Session = Depends(get_db)) -> Comment:
    try:
        _require_ticket(ticket_id, db)
        if db.get(User, payload.author_id) is None:
            raise HTTPException(status_code=404, detail=f"Author {payload.author_id} not found")

        comment = Comment(ticket_id=ticket_id, author_id=payload.author_id, body=payload.body)
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.get("/{ticket_id}/comments", response_model=list[CommentResponse])
def list_comments(ticket_id: int, db: Session = Depends(get_db)) -> list[Comment]:
    _require_ticket(ticket_id, db)
    statement = (
        select(Comment)
        .where(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    )
    return list(db.scalars(statement).all())


@router.get("/{ticket_id}/history", response_model=list[TicketStatusHistoryResponse])
def list_status_history(ticket_id: int, db: Session = Depends(get_db)) -> list[TicketStatusHistory]:
    _require_ticket(ticket_id, db)
    statement = (
        select(TicketStatusHistory)
        .where(TicketStatusHistory.ticket_id == ticket_id)
        .order_by(TicketStatusHistory.changed_at.asc(), TicketStatusHistory.id.asc())
    )
    return list(db.scalars(statement).all())
