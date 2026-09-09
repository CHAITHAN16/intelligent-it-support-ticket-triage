from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from celery_app import celery_app
from models import AssignmentSource, Ticket, TicketAssignment
from services.routing_service import RoutingService
from services.triage_service import TriageService


logger = logging.getLogger(__name__)


def create_task_session():
    from database import SessionLocal

    return SessionLocal()


def _has_completed_ai_processing(db, ticket_id: int) -> bool:
    assignment = db.scalar(
        select(TicketAssignment.id).where(
            TicketAssignment.ticket_id == ticket_id,
            TicketAssignment.source == AssignmentSource.AI,
        )
    )
    return assignment is not None


@celery_app.task(name="it_support.process_ticket")
def process_ticket(ticket_id: int) -> dict[str, int | str]:
    """Run AI triage and routing for a persisted ticket."""
    db = create_task_session()
    logger.info("Starting ticket processing: ticket_id=%s", ticket_id)

    try:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            logger.info("Skipping missing ticket: ticket_id=%s", ticket_id)
            return {"status": "missing", "ticket_id": ticket_id}

        if _has_completed_ai_processing(db, ticket_id):
            logger.info("Skipping already processed ticket: ticket_id=%s", ticket_id)
            return {"status": "already_processed", "ticket_id": ticket_id}

        triage_result = TriageService().triage(ticket.title, ticket.description)
        ticket.ai_predicted_category = triage_result.category
        ticket.ai_predicted_subcategory = triage_result.subcategory
        ticket.ai_predicted_priority = triage_result.priority
        ticket.ai_confidence = triage_result.confidence
        ticket.ai_model_version = triage_result.model_version
        created_at = ticket.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        ticket.ai_triaged_at = max(datetime.now(timezone.utc), created_at)
        ticket.updated_at = datetime.now(timezone.utc)

        RoutingService().route_and_assign(db, ticket, triage_result)
        db.commit()
        logger.info("Finished ticket processing: ticket_id=%s", ticket_id)
        return {"status": "processed", "ticket_id": ticket_id}
    except Exception:
        db.rollback()
        logger.exception("Ticket processing failed: ticket_id=%s", ticket_id)
        raise
    finally:
        db.close()
