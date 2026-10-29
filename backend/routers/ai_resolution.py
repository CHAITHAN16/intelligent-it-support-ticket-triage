from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import (
    AIResolutionConversation,
    AIResolutionMessage,
    KnowledgeBaseArticle,
    Ticket,
    TicketStatus,
    TicketStatusHistory,
    User,
    UserRole,
)
from routers.tickets import _require_ticket_access
from schemas.ai_resolution import (
    AIResolutionConfirmRequest,
    AIResolutionMessageCreate,
    AIResolutionResponse,
)
from services.ai_provider import AIProviderError
from services.ai_resolution_service import AIResolutionService
from services.resolution_service import evaluate_resolution_eligibility


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tickets", tags=["ai-resolution"])
_RESOLVABLE_STATUSES = {
    TicketStatus.NEW,
    TicketStatus.ASSIGNED,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_FOR_USER,
}


def _require_ticket(ticket_id: int, db: Session, current_user: User, *, employee_action: bool) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    _require_ticket_access(ticket, current_user, db)
    if employee_action and (current_user.role != UserRole.EMPLOYEE or ticket.creator_id != current_user.id):
        raise HTTPException(status_code=403, detail="Only the ticket's employee can use AI resolution actions")
    return ticket


def _find_conversation(ticket_id: int, db: Session) -> AIResolutionConversation | None:
    return db.scalar(
        select(AIResolutionConversation).where(AIResolutionConversation.ticket_id == ticket_id)
    )


def _article_and_decision(ticket: Ticket, db: Session):
    article = db.get(KnowledgeBaseArticle, ticket.knowledge_article_id) if ticket.knowledge_article_id else None
    article_is_available = article is not None and article.active
    decision = evaluate_resolution_eligibility(
        category=ticket.ai_predicted_category or ticket.category,
        title=ticket.title,
        description=ticket.description,
        classification_confidence=(
            float(ticket.ai_classification_confidence)
            if ticket.ai_classification_confidence is not None
            else None
        ),
        knowledge_match_status=ticket.solution_status if article_is_available else "NO_MATCH",
        knowledge_match_confidence=(
            float(ticket.solution_confidence) if ticket.solution_confidence is not None else None
        ),
    )
    return article if article_is_available else None, decision


def _response(
    ticket: Ticket,
    conversation: AIResolutionConversation | None,
    db: Session,
) -> AIResolutionResponse:
    _, decision = _article_and_decision(ticket, db)
    messages = []
    if conversation is not None:
        messages = db.scalars(
            select(AIResolutionMessage)
            .where(AIResolutionMessage.conversation_id == conversation.id)
            .order_by(AIResolutionMessage.created_at.asc(), AIResolutionMessage.id.asc())
        ).all()
    return AIResolutionResponse(
        status=conversation.status if conversation is not None else "NOT_STARTED",
        eligible=decision.eligible,
        escalation_reason=(
            conversation.escalation_reason
            if conversation is not None and conversation.escalation_reason
            else None if decision.eligible else decision.reason
        ),
        classification_confidence=decision.classification_confidence,
        knowledge_match_confidence=decision.knowledge_match_confidence,
        assigned_team_name=ticket.assigned_team_name,
        messages=messages,
    )


def _persist_escalation(
    ticket: Ticket,
    conversation: AIResolutionConversation,
    reason: str,
    db: Session,
) -> AIResolutionResponse:
    conversation.status = "ESCALATED"
    conversation.escalation_reason = reason
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _response(ticket, conversation, db)


def _generate_assistant_reply(
    ticket: Ticket,
    conversation: AIResolutionConversation,
    article: KnowledgeBaseArticle,
    db: Session,
) -> AIResolutionResponse:
    history = db.scalars(
        select(AIResolutionMessage)
        .where(AIResolutionMessage.conversation_id == conversation.id)
        .order_by(AIResolutionMessage.created_at.asc(), AIResolutionMessage.id.asc())
    ).all()
    service = AIResolutionService()
    try:
        reply = service.generate_reply(ticket, article, history)
    except AIProviderError as error:
        logger.warning(
            "AI resolution provider unavailable: ticket_id=%s error_type=%s",
            ticket.id,
            type(error).__name__,
        )
        return _persist_escalation(ticket, conversation, "AI_PROVIDER_UNAVAILABLE", db)
    except Exception as error:
        logger.error(
            "Unexpected AI resolution failure: ticket_id=%s error_type=%s",
            ticket.id,
            type(error).__name__,
        )
        return _persist_escalation(ticket, conversation, "AI_PROVIDER_UNAVAILABLE", db)

    if not reply.strip():
        return _persist_escalation(ticket, conversation, "AI_PROVIDER_UNAVAILABLE", db)

    provider = service.provider
    conversation.provider_model = getattr(provider, "model", None)
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(AIResolutionMessage(conversation_id=conversation.id, speaker="AI", body=reply.strip()))
    db.commit()
    return _response(ticket, conversation, db)


@router.get("/{ticket_id}/ai-resolution", response_model=AIResolutionResponse)
def get_ai_resolution(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIResolutionResponse:
    ticket = _require_ticket(ticket_id, db, current_user, employee_action=False)
    return _response(ticket, _find_conversation(ticket_id, db), db)


@router.post(
    "/{ticket_id}/ai-resolution/start",
    response_model=AIResolutionResponse,
    status_code=status.HTTP_200_OK,
)
def start_ai_resolution(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIResolutionResponse:
    ticket = _require_ticket(ticket_id, db, current_user, employee_action=True)
    article, decision = _article_and_decision(ticket, db)
    if ticket.ai_triaged_at is None:
        raise HTTPException(status_code=409, detail="Ticket triage is still processing")

    conversation = _find_conversation(ticket_id, db)
    if conversation is None:
        conversation = AIResolutionConversation(ticket_id=ticket.id)
        db.add(conversation)
        db.flush()
    if conversation.status != "ACTIVE" or db.scalar(
        select(AIResolutionMessage.id).where(
            AIResolutionMessage.conversation_id == conversation.id,
            AIResolutionMessage.speaker == "AI",
        )
    ) is not None:
        return _response(ticket, conversation, db)

    if not decision.eligible or article is None:
        return _persist_escalation(ticket, conversation, decision.reason, db)

    db.commit()
    return _generate_assistant_reply(ticket, conversation, article, db)


@router.post("/{ticket_id}/ai-resolution/messages", response_model=AIResolutionResponse)
def add_ai_resolution_message(
    ticket_id: int,
    payload: AIResolutionMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIResolutionResponse:
    ticket = _require_ticket(ticket_id, db, current_user, employee_action=True)
    conversation = _find_conversation(ticket_id, db)
    if conversation is None or conversation.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="This AI conversation is not active")
    article, decision = _article_and_decision(ticket, db)
    if not decision.eligible or article is None:
        return _persist_escalation(ticket, conversation, decision.reason, db)

    db.add(
        AIResolutionMessage(
            conversation_id=conversation.id,
            speaker="EMPLOYEE",
            author_id=current_user.id,
            body=payload.body,
        )
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _generate_assistant_reply(ticket, conversation, article, db)


@router.post("/{ticket_id}/ai-resolution/confirm", response_model=AIResolutionResponse)
def confirm_ai_resolution(
    ticket_id: int,
    payload: AIResolutionConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIResolutionResponse:
    ticket = _require_ticket(ticket_id, db, current_user, employee_action=True)
    conversation = _find_conversation(ticket_id, db)
    has_ai_reply = conversation is not None and db.scalar(
        select(AIResolutionMessage.id).where(
            AIResolutionMessage.conversation_id == conversation.id,
            AIResolutionMessage.speaker == "AI",
        )
    ) is not None
    if conversation is None or conversation.status != "ACTIVE" or not has_ai_reply:
        raise HTTPException(status_code=409, detail="An active AI-guided resolution is required")
    if ticket.status not in _RESOLVABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Ticket cannot be resolved from its current status")

    now = datetime.now(timezone.utc)
    old_status = ticket.status
    ticket.status = TicketStatus.RESOLVED
    ticket.resolved_at = now
    ticket.closed_at = None
    ticket.updated_at = now
    conversation.status = "RESOLVED"
    conversation.updated_at = now
    db.add(
        TicketStatusHistory(
            ticket_id=ticket.id,
            old_status=old_status,
            new_status=TicketStatus.RESOLVED,
            changed_by_id=current_user.id,
            note="Employee confirmed that the AI-guided troubleshooting resolved the issue.",
        )
    )
    db.commit()
    db.refresh(ticket)
    return _response(ticket, conversation, db)


@router.post("/{ticket_id}/ai-resolution/escalate", response_model=AIResolutionResponse)
def escalate_ai_resolution(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIResolutionResponse:
    ticket = _require_ticket(ticket_id, db, current_user, employee_action=True)
    conversation = _find_conversation(ticket_id, db)
    if conversation is None or conversation.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="This AI conversation is not active")
    return _persist_escalation(ticket, conversation, "EMPLOYEE_REQUESTED_HUMAN_SUPPORT", db)