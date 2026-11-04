import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Ticket, TicketPriority, TicketStatus, User, UserRole
from services.confidence_backfill import backfill_missing_classification_confidence
from services.triage_service import (
    MODEL_VERSION,
    ConfidencePredictionMismatchError,
)


@pytest.fixture
def backfill_database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    now = datetime.now(timezone.utc)
    db.add(
        User(
            id=1,
            name="Employee",
            email="employee@example.com",
            role=UserRole.EMPLOYEE,
        )
    )
    db.commit()
    yield db
    db.close()
    Base.metadata.drop_all(engine)


def add_ticket(db, ticket_id, *, confidence=None, model_version=MODEL_VERSION, triaged=True):
    now = datetime.now(timezone.utc)
    ticket = Ticket(
        id=ticket_id,
        title="VPN outage",
        description="The company VPN is unavailable.",
        creator_id=1,
        category="Network",
        priority=TicketPriority.HIGH,
        status=TicketStatus.IN_PROGRESS,
        assigned_team_id=None,
        assigned_agent_id=None,
        ai_predicted_category="Network",
        ai_predicted_priority=TicketPriority.HIGH,
        ai_confidence=0.91,
        ai_classification_confidence=confidence,
        ai_model_version=model_version,
        ai_triaged_at=now if triaged else None,
        routing_reason="Existing routing reason",
        solution_status="MATCHED",
        suggested_solution="Existing recommendation",
        knowledge_article_id=None,
        solution_confidence=0.82,
        created_at=now,
        updated_at=now,
    )
    db.add(ticket)
    db.commit()
    return ticket


class FixedConfidenceService:
    def __init__(self, confidence=0.73, error=None):
        self.confidence = confidence
        self.error = error
        self.calls = []

    def classification_confidence_for_category(
        self, title, description, expected_category
    ):
        self.calls.append((title, description, expected_category))
        if self.error is not None:
            raise self.error
        return self.confidence


def test_backfill_dry_run_reports_eligible_without_writing(backfill_database):
    ticket = add_ticket(backfill_database, 1)
    service = FixedConfidenceService()
    original_updated_at = ticket.updated_at

    summary = backfill_missing_classification_confidence(
        backfill_database, triage_service=service
    )

    backfill_database.expire_all()
    assert summary.scanned == 1
    assert summary.ready == 1
    assert summary.updated == 0
    assert service.calls == [
        ("VPN outage", "The company VPN is unavailable.", "Network")
    ]
    assert backfill_database.get(Ticket, 1).ai_classification_confidence is None
    assert backfill_database.get(Ticket, 1).updated_at == original_updated_at


def test_backfill_applies_only_confidence_and_is_idempotent(backfill_database):
    ticket = add_ticket(backfill_database, 1)
    immutable_values = {
        "category": ticket.category,
        "subcategory": ticket.subcategory,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_team_id": ticket.assigned_team_id,
        "assigned_agent_id": ticket.assigned_agent_id,
        "ai_predicted_category": ticket.ai_predicted_category,
        "ai_predicted_priority": ticket.ai_predicted_priority,
        "ai_confidence": ticket.ai_confidence,
        "ai_model_version": ticket.ai_model_version,
        "ai_triaged_at": ticket.ai_triaged_at,
        "routing_reason": ticket.routing_reason,
        "solution_status": ticket.solution_status,
        "suggested_solution": ticket.suggested_solution,
        "knowledge_article_id": ticket.knowledge_article_id,
        "solution_confidence": ticket.solution_confidence,
        "updated_at": ticket.updated_at,
    }

    first = backfill_missing_classification_confidence(
        backfill_database, apply=True, triage_service=FixedConfidenceService()
    )
    backfill_database.expire_all()
    ticket = backfill_database.get(Ticket, 1)

    assert first.updated == 1
    assert float(ticket.ai_classification_confidence) == pytest.approx(0.73)
    assert {
        key: getattr(ticket, key) for key in immutable_values
    } == immutable_values

    second = backfill_missing_classification_confidence(
        backfill_database, apply=True, triage_service=FixedConfidenceService()
    )
    assert second.scanned == 0
    assert second.updated == 0


@pytest.mark.parametrize(
    ("model_version", "triaged", "expected_reason"),
    [
        ("unavailable-model", True, "unsupported_or_missing_model_version"),
        (MODEL_VERSION, False, "not_triaged"),
    ],
)
def test_backfill_skips_records_without_supported_model_evidence(
    backfill_database, model_version, triaged, expected_reason
):
    add_ticket(
        backfill_database,
        1,
        model_version=model_version,
        triaged=triaged,
    )
    service = FixedConfidenceService()

    summary = backfill_missing_classification_confidence(
        backfill_database, apply=True, triage_service=service
    )

    backfill_database.expire_all()
    assert summary.updated == 0
    assert summary.skipped == {expected_reason: 1}
    assert service.calls == []
    assert backfill_database.get(Ticket, 1).ai_classification_confidence is None


def test_backfill_skips_when_model_category_does_not_match(backfill_database):
    add_ticket(backfill_database, 1)
    service = FixedConfidenceService(
        error=ConfidencePredictionMismatchError("category differs")
    )

    summary = backfill_missing_classification_confidence(
        backfill_database, apply=True, triage_service=service
    )

    backfill_database.expire_all()
    assert summary.ready == 0
    assert summary.updated == 0
    assert summary.skipped == {"current_model_prediction_mismatch": 1}
    assert backfill_database.get(Ticket, 1).ai_classification_confidence is None
