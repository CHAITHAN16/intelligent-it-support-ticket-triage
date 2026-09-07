from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import Comment, Ticket, TicketStatusHistory, User, UserRole
from routers.tickets import _require_ticket_access, _can_agent_access_ticket
from schemas.collaboration import CommentCreate, CommentResponse, TicketStatusHistoryResponse


router = APIRouter(prefix="/api/tickets", tags=["ticket-collaboration"])


def _require_ticket(ticket_id: int, db: Session) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    ticket_id: int,
    payload: CommentCreate,
    current_user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Comment:
    try:
        ticket = _require_ticket(ticket_id, db)
        if isinstance(current_user, User):
            if current_user.role not in (UserRole.SUPPORT_AGENT, UserRole.ADMIN) or not _can_agent_access_ticket(ticket, current_user, db):
                raise HTTPException(status_code=403, detail="Only an authorized agent can create comments")
            author_id = current_user.id
        else:
            author_id = payload.author_id
            if author_id is None:
                raise HTTPException(status_code=401, detail="Authentication is required")
            if db.get(User, author_id) is None:
                raise HTTPException(status_code=404, detail=f"Author {author_id} not found")

        comment = Comment(ticket_id=ticket_id, author_id=author_id, body=payload.body)
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
def list_comments(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Comment]:
    ticket = _require_ticket(ticket_id, db)
    _require_ticket_access(ticket, current_user, db)
    statement = (
        select(Comment)
        .where(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    )
    return list(db.scalars(statement).all())


@router.get("/{ticket_id}/history", response_model=list[TicketStatusHistoryResponse])
def list_status_history(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TicketStatusHistory]:
    ticket = _require_ticket(ticket_id, db)
    _require_ticket_access(ticket, current_user, db)
    statement = (
        select(TicketStatusHistory)
        .where(TicketStatusHistory.ticket_id == ticket_id)
        .order_by(TicketStatusHistory.changed_at.asc(), TicketStatusHistory.id.asc())
    )
    return list(db.scalars(statement).all())
