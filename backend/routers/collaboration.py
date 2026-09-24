from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user, require_agent
from models import Comment, Ticket, TicketAssignment, TicketFieldHistory, TicketStatusHistory, User, UserRole
from routers.tickets import _require_ticket_access, _can_agent_access_ticket
from schemas.collaboration import CommentCreate, CommentResponse, TicketFieldHistoryResponse, TicketStatusHistoryResponse
from schemas.tickets import TicketAssignmentResponse


router = APIRouter(prefix="/api/tickets", tags=["ticket-collaboration"])


def _require_ticket(ticket_id: int, db: Session) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a ticket comment",
    description="Create a comment on a ticket. Authenticated agents must be authorized for the ticket; unauthenticated service callers must provide an existing author_id.",
    response_description="The created comment.",
    responses={401: {"description": "Authentication or an author_id is required."}, 403: {"description": "The agent cannot comment on this ticket."}, 404: {"description": "The ticket or specified author does not exist."}, 422: {"description": "The request body failed validation."}},
)
def create_comment(
    ticket_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_agent),
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


@router.get(
    "/{ticket_id}/comments",
    response_model=list[CommentResponse],
    summary="List ticket comments",
    description="List comments for a ticket in creation order, if the current user can access the ticket.",
    response_description="The ticket's comments.",
    responses={401: {"description": "Authentication is required."}, 403: {"description": "The user cannot access this ticket."}, 404: {"description": "The ticket does not exist."}},
)
def list_comments(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Comment]:
    ticket = _require_ticket(ticket_id, db)
    _require_ticket_access(ticket, current_user, db)
    statement = (
        select(Comment)
        .where(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    )
    return list(db.scalars(statement).all())


@router.get(
    "/{ticket_id}/history",
    response_model=list[TicketStatusHistoryResponse],
    summary="List ticket status history",
    description="List status changes for a ticket in chronological order, if the current user can access it.",
    response_description="The ticket's status history.",
    responses={401: {"description": "Authentication is required."}, 403: {"description": "The user cannot access this ticket."}, 404: {"description": "The ticket does not exist."}},
)
def list_status_history(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TicketStatusHistory]:
    ticket = _require_ticket(ticket_id, db)
    _require_ticket_access(ticket, current_user, db)
    statement = (
        select(TicketStatusHistory)
        .where(TicketStatusHistory.ticket_id == ticket_id)
        .order_by(TicketStatusHistory.changed_at.asc(), TicketStatusHistory.id.asc())
    )
    return list(db.scalars(statement).all())


@router.get(
    "/{ticket_id}/field-history",
    response_model=list[TicketFieldHistoryResponse],
    summary="List ticket classification history",
    description="List recorded category, subcategory, and priority changes for a ticket, if the current user can access it.",
    response_description="The ticket's classification history.",
    responses={401: {"description": "Authentication is required."}, 403: {"description": "The user cannot access this ticket."}, 404: {"description": "The ticket does not exist."}},
)
def list_field_history(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TicketFieldHistory]:
    ticket = _require_ticket(ticket_id, db)
    _require_ticket_access(ticket, current_user, db)
    return list(db.scalars(
        select(TicketFieldHistory)
        .where(TicketFieldHistory.ticket_id == ticket_id)
        .order_by(TicketFieldHistory.changed_at.asc(), TicketFieldHistory.id.asc())
    ).all())


@router.get(
    "/{ticket_id}/assignments",
    response_model=list[TicketAssignmentResponse],
    summary="List ticket assignment history",
    description="List team and agent assignments for a ticket in assignment order, if the current user can access it.",
    response_description="The ticket's assignment history.",
    responses={401: {"description": "Authentication is required."}, 403: {"description": "The user cannot access this ticket."}, 404: {"description": "The ticket does not exist."}},
)
def list_assignment_history(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TicketAssignment]:
    ticket = _require_ticket(ticket_id, db)
    _require_ticket_access(ticket, current_user, db)
    return list(db.scalars(
        select(TicketAssignment)
        .where(TicketAssignment.ticket_id == ticket_id)
        .order_by(TicketAssignment.assigned_at.asc(), TicketAssignment.id.asc())
    ).all())
