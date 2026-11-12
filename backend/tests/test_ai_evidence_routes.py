import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from auth import create_access_token
from database import get_db
from main import app
from models import (
    Base,
    Team,
    TeamMember,
    Ticket,
    TicketFieldHistory,
    TicketPredictionEvidence,
    TicketPredictionReview,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)


@pytest.fixture
def evidence_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    next_ids = {TicketPredictionEvidence: 1, TicketPredictionReview: 1, TicketFieldHistory: 1}

    def assign_ids(session, flush_context, instances):
        for value in session.new:
            if type(value) in next_ids and value.id is None:
                value.id = next_ids[type(value)]
                next_ids[type(value)] += 1

    event.listen(Session, "before_flush", assign_ids)
    now = datetime.now(timezone.utc)
    db.add_all(
        [
            User(id=1, name="Employee", email="employee@example.com", role=UserRole.EMPLOYEE),
            User(id=2, name="Agent", email="agent@example.com", role=UserRole.SUPPORT_AGENT),
            User(id=3, name="Other agent", email="other@example.com", role=UserRole.SUPPORT_AGENT),
            Team(id=1, name="Network"),
            Team(id=2, name="Security"),
            TeamMember(team_id=1, user_id=2, member_role=UserRole.SUPPORT_AGENT),
            Ticket(id=1, title="VPN", description="VPN issue", creator_id=1, assigned_team_id=1, category="Software", priority=TicketPriority.MEDIUM, status=TicketStatus.NEW, created_at=now, updated_at=now),
            Ticket(id=2, title="Firewall", description="Firewall issue", creator_id=1, assigned_team_id=2, category="Security", priority=TicketPriority.LOW, status=TicketStatus.NEW, created_at=now, updated_at=now),
            TicketPredictionEvidence(id=1, ticket_id=1, predicted_category="Network", predicted_priority=TicketPriority.HIGH, category_model_version="category-v1", priority_model_version="priority-v2", runtime_model_version="category-v1+priority-v2", category_probabilities={"Network": 0.8, "Software": 0.2}, priority_probabilities={"LOW": 0.1, "MEDIUM": 0.2, "HIGH": 0.7}, classification_confidence=0.8, combined_confidence=0.75, predicted_at=now),
            TicketPredictionEvidence(id=2, ticket_id=2, predicted_category="Security", predicted_priority=TicketPriority.LOW, category_model_version="category-v1", priority_model_version="priority-v2", runtime_model_version="category-v1+priority-v2", category_probabilities={"Security": 1.0}, priority_probabilities={"LOW": 1.0}, classification_confidence=1.0, combined_confidence=1.0, predicted_at=now),
        ]
    )
    db.commit()
    yield db
    event.remove(Session, "before_flush", assign_ids)
    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def evidence_client(evidence_db):
    app.dependency_overrides[get_db] = lambda: evidence_db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


def headers(db, user_id):
    return {"Authorization": f"Bearer {create_access_token(db.get(User, user_id))}"}


def review(evidence_id=1, **kwargs):
    return {"prediction_evidence_id": evidence_id, **kwargs}


def test_evidence_endpoint_returns_stored_probability_evidence(evidence_client, evidence_db):
    response = evidence_client.get("/api/tickets/1/prediction-evidence", headers=headers(evidence_db, 2))
    assert response.status_code == 200
    assert response.json()[0]["category_probabilities"] == {"Network": 0.8, "Software": 0.2}
    assert response.json()[0]["priority_probabilities"]["HIGH"] == 0.7


def test_agent_can_accept_predictions_without_changing_ticket_values(evidence_client, evidence_db):
    response = evidence_client.post(
        "/api/tickets/1/prediction-reviews",
        headers=headers(evidence_db, 2),
        json=review(category="Network", priority="HIGH"),
    )
    assert response.status_code == 201
    assert [row["outcome"] for row in response.json()] == ["ACCEPTED", "ACCEPTED"]
    assert evidence_db.get(Ticket, 1).category == "Software"
    assert evidence_db.get(Ticket, 1).priority == TicketPriority.MEDIUM


def test_category_override_updates_ticket_and_records_field_history(evidence_client, evidence_db):
    response = evidence_client.post(
        "/api/tickets/1/prediction-reviews",
        headers=headers(evidence_db, 2),
        json=review(category="Security", reason="Agent confirmed security issue"),
    )
    assert response.status_code == 201
    assert response.json()[0]["outcome"] == "OVERRIDDEN"
    assert response.json()[0]["confirmed_value"] == "Security"
    assert evidence_db.get(Ticket, 1).category == "Security"
    history = evidence_db.query(TicketFieldHistory).one()
    assert (history.field_name, history.old_value, history.new_value, history.changed_by_id) == ("category", "Software", "Security", 2)


def test_priority_partial_review_records_only_priority_and_applies_override(evidence_client, evidence_db):
    response = evidence_client.post(
        "/api/tickets/1/prediction-reviews",
        headers=headers(evidence_db, 2),
        json=review(priority="LOW"),
    )
    assert response.status_code == 201
    assert len(response.json()) == 1
    assert response.json()[0]["field_name"] == "priority"
    assert evidence_db.get(Ticket, 1).priority == TicketPriority.LOW
    assert evidence_db.query(TicketPredictionReview).count() == 1


def test_review_is_bound_to_snapshot_and_duplicate_field_review_is_rejected(evidence_client, evidence_db):
    first = evidence_client.post(
        "/api/tickets/1/prediction-reviews",
        headers=headers(evidence_db, 2),
        json=review(category="Network"),
    )
    assert first.status_code == 201
    duplicate = evidence_client.post(
        "/api/tickets/1/prediction-reviews",
        headers=headers(evidence_db, 2),
        json=review(category="Security"),
    )
    assert duplicate.status_code == 409
    assert evidence_db.query(TicketPredictionReview).count() == 1
    assert evidence_db.get(Ticket, 1).category == "Software"

    history = evidence_client.get(
        "/api/tickets/1/prediction-reviews", headers=headers(evidence_db, 2)
    )
    assert history.status_code == 200
    assert history.json()[0]["prediction_evidence_id"] == 1
    assert history.json()[0]["reviewer_name"] == "Agent"


@pytest.mark.parametrize("payload", [
    {"prediction_evidence_id": 1, "category": "Unknown"},
    {"prediction_evidence_id": 1, "priority": "P0"},
    {"prediction_evidence_id": 1},
])
def test_invalid_or_empty_review_is_rejected(evidence_client, evidence_db, payload):
    response = evidence_client.post("/api/tickets/1/prediction-reviews", headers=headers(evidence_db, 2), json=payload)
    assert response.status_code == 422
    assert evidence_db.query(TicketPredictionReview).count() == 0


def test_employee_cannot_read_or_submit_agent_reviews(evidence_client, evidence_db):
    employee_headers = headers(evidence_db, 1)
    assert evidence_client.get("/api/tickets/1/prediction-evidence", headers=employee_headers).status_code == 403
    assert evidence_client.post("/api/tickets/1/prediction-reviews", headers=employee_headers, json=review(category="Network")).status_code == 403


def test_ai_analytics_uses_latest_snapshot_and_agent_ticket_scope(evidence_client, evidence_db):
    now = datetime.now(timezone.utc)
    evidence_db.add(TicketPredictionReview(
        ticket_id=1, prediction_evidence_id=1, reviewer_id=2, field_name="category",
        predicted_value="Network", confirmed_value="Network", outcome="ACCEPTED", reviewed_at=now,
    ))
    evidence_db.commit()
    date_value = now.date().isoformat()
    response = evidence_client.get(
        f"/api/analytics/ai?from={date_value}&to={date_value}", headers=headers(evidence_db, 2)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # The agent only sees team 1; ticket 2 belongs to another team.
    assert body["total_prediction_tickets"] == 1
    assert body["reviewed_prediction_tickets"] == 1
    assert body["category"] == {"reviewed": 1, "accepted": 1, "overridden": 0, "acceptance_rate": 1.0, "override_rate": 0.0}
    assert body["priority"]["reviewed"] == 0


def test_employee_cannot_read_ai_analytics(evidence_client, evidence_db):
    date_value = datetime.now(timezone.utc).date().isoformat()
    response = evidence_client.get(
        f"/api/analytics/ai?from={date_value}&to={date_value}", headers=headers(evidence_db, 1)
    )
    assert response.status_code == 403


def test_agent_ticket_scope_and_evidence_scope_are_enforced(evidence_client, evidence_db):
    agent_headers = headers(evidence_db, 2)
    assert evidence_client.get("/api/tickets/2/prediction-evidence", headers=agent_headers).status_code == 403
    response = evidence_client.post("/api/tickets/1/prediction-reviews", headers=agent_headers, json=review(evidence_id=2, category="Security"))
    assert response.status_code == 404
    assert evidence_db.query(TicketPredictionReview).count() == 0


def test_review_transaction_rolls_back_ticket_history_and_review(evidence_client, evidence_db, monkeypatch):
    def fail_commit():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(evidence_db, "commit", fail_commit)
    response = evidence_client.post(
        "/api/tickets/1/prediction-reviews",
        headers=headers(evidence_db, 2),
        json=review(category="Security"),
    )
    assert response.status_code == 500
    evidence_db.rollback()
    assert evidence_db.query(TicketPredictionReview).count() == 0
    assert evidence_db.query(TicketFieldHistory).count() == 0
    assert evidence_db.get(Ticket, 1).category == "Software"
