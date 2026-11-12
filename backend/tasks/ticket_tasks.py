from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from celery_app import celery_app
from database import SessionLocal
from models import AssignmentSource, Ticket, TicketAssignment, TicketPredictionEvidence
from services.routing_service import RoutingService
from services.triage_service import (
    MODEL_VERSION,
    ConfidencePredictionMismatchError,
    TriageService,
)
from services.knowledge_base_service import KnowledgeBaseService


logger = logging.getLogger(__name__)


def create_task_session():
    return SessionLocal()


def _has_completed_core_ai_processing(
    ticket: Ticket, assignment: TicketAssignment | None
) -> bool:
    return bool(
        ticket.ai_predicted_category
        and ticket.category
        and ticket.ai_model_version
        and ticket.ai_triaged_at is not None
        and ticket.assigned_team_id is not None
        and ticket.solution_status in {"MATCHED", "NO_MATCH"}
        and assignment is not None
    )


def _has_completed_ai_processing(
    ticket: Ticket, assignment: TicketAssignment | None
) -> bool:
    return (
        _has_completed_core_ai_processing(ticket, assignment)
        and ticket.ai_classification_confidence is not None
    )


@celery_app.task(
    name="it_support.process_ticket",
    autoretry_for=(OperationalError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def process_ticket(ticket_id: int) -> dict[str, int | str]:
    """Run AI triage and routing for a persisted ticket."""
    db = create_task_session()
    logger.info("Starting ticket processing: ticket_id=%s", ticket_id)

    try:
        ticket = db.scalar(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            # assigned_team is configured with lazy="joined", which adds a
            # nullable LEFT OUTER JOIN. PostgreSQL cannot lock the nullable
            # side of that join, so scope the row lock to the ticket itself.
            .with_for_update(of=Ticket)
        )
        if ticket is None:
            logger.info("Skipping missing ticket: ticket_id=%s", ticket_id)
            return {"status": "missing", "ticket_id": ticket_id}

        existing_assignment = db.scalar(
            select(TicketAssignment).where(
                TicketAssignment.ticket_id == ticket_id,
                TicketAssignment.source == AssignmentSource.AI,
            )
        )
        if _has_completed_core_ai_processing(ticket, existing_assignment):
            if _has_completed_ai_processing(ticket, existing_assignment):
                logger.info("Skipping already processed ticket: ticket_id=%s", ticket_id)
                return {"status": "already_processed", "ticket_id": ticket_id}

            if ticket.ai_model_version != MODEL_VERSION:
                logger.warning(
                    "Cannot repair classification confidence with an unavailable "
                    "model version: ticket_id=%s model_version=%s",
                    ticket_id,
                    ticket.ai_model_version,
                )
                return {"status": "confidence_unavailable", "ticket_id": ticket_id}
            if not ticket.ai_predicted_category:
                logger.warning(
                    "Cannot repair classification confidence without a stored "
                    "category prediction: ticket_id=%s",
                    ticket_id,
                )
                return {"status": "confidence_unavailable", "ticket_id": ticket_id}

            try:
                confidence = TriageService().classification_confidence_for_category(
                    ticket.title,
                    ticket.description,
                    ticket.ai_predicted_category,
                )
            except ConfidencePredictionMismatchError:
                logger.exception(
                    "Configured model does not reproduce the stored category; "
                    "leaving ticket unchanged: ticket_id=%s",
                    ticket_id,
                )
                return {"status": "confidence_unavailable", "ticket_id": ticket_id}

            ticket.ai_classification_confidence = confidence
            db.commit()
            logger.info(
                "Repaired classification confidence without rerunning triage: "
                "ticket_id=%s",
                ticket_id,
            )
            return {"status": "confidence_repaired", "ticket_id": ticket_id}

        triage_result = TriageService().triage(ticket.title, ticket.description)
        if triage_result.classification_confidence is None:
            raise RuntimeError(
                "Triage model returned no classification confidence for "
                f"ticket_id={ticket_id}"
            )
        ticket.category = triage_result.category
        if triage_result.subcategory is not None:
            ticket.subcategory = triage_result.subcategory
        ticket.ai_predicted_category = triage_result.category
        ticket.ai_predicted_subcategory = triage_result.subcategory
        ticket.ai_predicted_priority = triage_result.priority
        ticket.ai_confidence = triage_result.confidence
        ticket.ai_classification_confidence = triage_result.classification_confidence
        ticket.ai_model_version = triage_result.model_version
        created_at = ticket.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        ticket.ai_triaged_at = max(datetime.now(timezone.utc), created_at)
        ticket.updated_at = datetime.now(timezone.utc)
        db.add(
            TicketPredictionEvidence(
                ticket_id=ticket.id,
                predicted_category=triage_result.category,
                predicted_priority=triage_result.priority,
                category_model_version=triage_result.category_model_version,
                priority_model_version=triage_result.priority_model_version,
                runtime_model_version=triage_result.model_version,
                category_probabilities=triage_result.category_probabilities,
                priority_probabilities=triage_result.priority_probabilities,
                classification_confidence=triage_result.classification_confidence,
                combined_confidence=triage_result.confidence,
                predicted_at=ticket.ai_triaged_at,
            )
        )

        if existing_assignment is None:
            RoutingService().route_and_assign(db, ticket, triage_result)
        else:
            ticket.assigned_team_id = existing_assignment.team_id
            ticket.routing_reason = existing_assignment.routing_reason

        # Flush primary triage and routing before opening a savepoint. Any
        # failure here must still fail the task; only KB retrieval is optional.
        db.flush()
        try:
            with db.begin_nested():
                solution = KnowledgeBaseService().retrieve(
                    db, ticket.title, ticket.description, triage_result.category
                )
        except Exception:
            logger.exception(
                "Knowledge-base retrieval failed; continuing without recommendation: ticket_id=%s",
                ticket_id,
            )
            ticket.solution_status = "NO_MATCH"
            ticket.suggested_solution = None
            ticket.knowledge_article_id = None
            ticket.solution_confidence = None
        else:
            ticket.solution_status = solution.status
            ticket.suggested_solution = solution.suggested_solution
            ticket.knowledge_article_id = solution.article_id
            ticket.solution_confidence = solution.confidence
        db.commit()
        logger.info("Finished ticket processing: ticket_id=%s", ticket_id)
        return {"status": "processed", "ticket_id": ticket_id}
    except Exception:
        db.rollback()
        logger.exception("Ticket processing failed: ticket_id=%s", ticket_id)
        raise
    finally:
        db.close()
