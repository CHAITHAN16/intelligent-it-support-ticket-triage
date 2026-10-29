import os
from datetime import datetime, timezone
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from auth import get_current_user
from database import get_db
from main import app
from models import (
    AIResolutionConversation,
    AIResolutionMessage,
    Base,
    KnowledgeBaseArticle,
    Ticket,
    TicketPriority,
    TicketStatus,
    TicketStatusHistory,
    User,
    UserRole,
)
from services.ai_provider import AIProviderUnavailable


@pytest.fixture
def resolution_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    next_ids = {AIResolutionConversation: 1, AIResolutionMessage: 1, TicketStatusHistory: 1}

    def assign_identity_ids(db_session, _flush_context, _instances):
        for value in db_session.new:
            if type(value) in next_ids and value.id is None:
                value.id = next_ids[type(value)]
                next_ids[type(value)] += 1

    event.listen(Session, "before_flush", assign_identity_ids)
    now = datetime.now(timezone.utc)
    session.add_all(
        [
            User(id=1, name="Employee", email="employee@test.local", role=UserRole.EMPLOYEE),
            User(id=2, name="Other Employee", email="other@test.local", role=UserRole.EMPLOYEE),
            KnowledgeBaseArticle(
                id=1,
                title="Approved application login steps",
                summary="Refresh the application's sign-in session.",
                category="Software",
                resolution_steps="Close and reopen the approved application.",
                keywords="login application",
                active=True,
            ),
            Ticket(
                id=1,
                title="Approved application closes",
                description="The approved application closes after sign-in.",
                category="Software",
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.NEW,
                creator_id=1,
                ai_predicted_category="Software",
                ai_confidence=0.82,
                ai_classification_confidence=0.82,
                ai_triaged_at=now,
                solution_status="MATCHED",
                suggested_solution="Close and reopen the approved application.",
                knowledge_article_id=1,
                solution_confidence=0.80,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    session.commit()
    yield session
    event.remove(Session, "before_flush", assign_identity_ids)
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def resolution_client(resolution_session):
    def override_get_db():
        yield resolution_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: resolution_session.get(User, 1)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class FakeResolutionService:
    provider = SimpleNamespace(model="test-model")

    def generate_reply(self, _ticket, _article, _history):
        return "Close and reopen the approved application, then tell me what happens."


def test_start_persists_assistant_reply_without_resolving_ticket(
    resolution_client, resolution_session, monkeypatch
):
    monkeypatch.setattr("routers.ai_resolution.AIResolutionService", FakeResolutionService)

    response = resolution_client.post("/api/tickets/1/ai-resolution/start")

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["messages"][0]["speaker"] == "AI"
    ticket = resolution_session.get(Ticket, 1)
    assert ticket.status == TicketStatus.NEW
    assert ticket.resolved_at is None
    assert resolution_session.query(AIResolutionMessage).count() == 1


@pytest.mark.parametrize(
    ("ticket_updates", "expected_reason"),
    [
        ({"ai_classification_confidence": 0.74}, "LOW_CLASSIFICATION_CONFIDENCE"),
        ({"ai_predicted_category": "Security", "category": "Security"}, "SECURITY_SENSITIVE"),
    ],
)
def test_ineligible_ticket_escalates_without_calling_provider(
    resolution_client, resolution_session, monkeypatch, ticket_updates, expected_reason
):
    ticket = resolution_session.get(Ticket, 1)
    for field, value in ticket_updates.items():
        setattr(ticket, field, value)
    resolution_session.commit()

    def provider_must_not_run(*_args, **_kwargs):
        pytest.fail("provider must not run for an ineligible ticket")

    monkeypatch.setattr("routers.ai_resolution.AIResolutionService", provider_must_not_run)
    response = resolution_client.post("/api/tickets/1/ai-resolution/start")

    assert response.status_code == 200
    assert response.json()["status"] == "ESCALATED"
    assert response.json()["escalation_reason"] == expected_reason
    assert response.json()["messages"] == []
    assert resolution_session.get(Ticket, 1).status == TicketStatus.NEW


def test_employee_reply_is_persisted_and_sent_for_follow_up(
    resolution_client, resolution_session, monkeypatch
):
    monkeypatch.setattr("routers.ai_resolution.AIResolutionService", FakeResolutionService)
    resolution_client.post("/api/tickets/1/ai-resolution/start")

    response = resolution_client.post(
        "/api/tickets/1/ai-resolution/messages",
        json={"body": "I tried that and the sign-in window still closes."},
    )

    assert response.status_code == 200
    assert [message["speaker"] for message in response.json()["messages"]] == ["AI", "EMPLOYEE", "AI"]
    employee_message = resolution_session.query(AIResolutionMessage).filter_by(speaker="EMPLOYEE").one()
    assert employee_message.author_id == 1
    assert employee_message.body == "I tried that and the sign-in window still closes."


def test_provider_failure_escalates_and_preserves_unresolved_ticket(
    resolution_client, resolution_session, monkeypatch
):
    class FailedService:
        provider = None

        def generate_reply(self, *_args, **_kwargs):
            raise AIProviderUnavailable("provider timeout")

    monkeypatch.setattr("routers.ai_resolution.AIResolutionService", FailedService)

    response = resolution_client.post("/api/tickets/1/ai-resolution/start")

    assert response.status_code == 200
    assert response.json()["status"] == "ESCALATED"
    assert response.json()["escalation_reason"] == "AI_PROVIDER_UNAVAILABLE"
    assert resolution_session.get(Ticket, 1).status == TicketStatus.NEW


def test_invalid_threshold_fails_closed_to_human_team(
    resolution_client, resolution_session, monkeypatch
):
    monkeypatch.setenv("AI_RESOLUTION_CONFIDENCE_THRESHOLD", "invalid")
    monkeypatch.setattr(
        "routers.ai_resolution.AIResolutionService",
        lambda: pytest.fail("provider must not run with invalid threshold configuration"),
    )

    response = resolution_client.post("/api/tickets/1/ai-resolution/start")

    assert response.status_code == 200
    assert response.json()["status"] == "ESCALATED"
    assert response.json()["escalation_reason"] == "AI_CONFIGURATION_INVALID"
    assert resolution_session.get(Ticket, 1).status == TicketStatus.NEW


def test_only_employee_confirmation_resolves_ai_guided_ticket(
    resolution_client, resolution_session, monkeypatch
):
    monkeypatch.setattr("routers.ai_resolution.AIResolutionService", FakeResolutionService)
    resolution_client.post("/api/tickets/1/ai-resolution/start")
    assert resolution_session.get(Ticket, 1).status == TicketStatus.NEW

    response = resolution_client.post(
        "/api/tickets/1/ai-resolution/confirm",
        json={"confirmed": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"
    assert resolution_session.get(Ticket, 1).status == TicketStatus.RESOLVED
    history = resolution_session.query(TicketStatusHistory).one()
    assert history.changed_by_id == 1
    assert "Employee confirmed" in history.note


def test_confirmation_is_rejected_without_prior_ai_guidance(resolution_client, resolution_session):
    response = resolution_client.post(
        "/api/tickets/1/ai-resolution/confirm",
        json={"confirmed": True},
    )

    assert response.status_code == 409
    assert resolution_session.get(Ticket, 1).status == TicketStatus.NEW


def test_another_employee_cannot_use_ticket_resolution(resolution_client, resolution_session):
    app.dependency_overrides[get_current_user] = lambda: resolution_session.get(User, 2)

    response = resolution_client.post("/api/tickets/1/ai-resolution/start")

    assert response.status_code == 403