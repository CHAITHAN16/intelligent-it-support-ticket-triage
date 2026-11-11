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
    assert response.json()["mode"] == "GUIDED"
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
def test_ineligible_ticket_starts_provider_free_basic_assistance(
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
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["mode"] == "BASIC"
    assert response.json()["eligibility_reason"] == expected_reason
    assert "Current status: NEW" in response.json()["messages"][0]["body"]
    assert "Predicted category:" in response.json()["messages"][0]["body"]
    assert resolution_session.get(Ticket, 1).status == TicketStatus.NEW


def test_basic_assistance_is_available_before_triage_and_never_calls_provider(
    resolution_client, resolution_session, monkeypatch
):
    ticket = resolution_session.get(Ticket, 1)
    ticket.ai_triaged_at = None
    ticket.ai_classification_confidence = None
    ticket.ai_predicted_category = None
    ticket.ai_predicted_priority = None
    ticket.solution_status = None
    ticket.knowledge_article_id = None
    resolution_session.commit()
    monkeypatch.setattr(
        "routers.ai_resolution.AIResolutionService",
        lambda: pytest.fail("basic assistance must not create a provider"),
    )

    response = resolution_client.post("/api/tickets/1/ai-resolution/start")

    assert response.status_code == 200
    assert response.json()["mode"] == "BASIC"
    assert "not available yet" in response.json()["messages"][0]["body"]


def test_basic_follow_up_persists_messages_without_provider(
    resolution_client, resolution_session, monkeypatch
):
    ticket = resolution_session.get(Ticket, 1)
    ticket.ai_classification_confidence = 0.20
    ticket.title = "VPN connection issue"
    ticket.description = "VPN fails to connect."
    ticket.category = "Network"
    ticket.ai_predicted_category = "Network"
    resolution_session.commit()
    monkeypatch.setattr(
        "routers.ai_resolution.AIResolutionService",
        lambda: pytest.fail("basic assistance must not create a provider"),
    )
    resolution_client.post("/api/tickets/1/ai-resolution/start")

    response = resolution_client.post(
        "/api/tickets/1/ai-resolution/messages",
        json={"body": "The VPN issue started this morning. Only my laptop is affected. I get a connection timed out error whenever I try to connect."},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "BASIC"
    assert [message["speaker"] for message in response.json()["messages"]] == ["AI", "EMPLOYEE", "AI"]
    context = response.json()["basic_context"]
    assert context["start_time"] == "this morning"
    assert context["affected_devices_users"] == "One device: laptop"
    assert context["affected_service"] == "VPN"
    assert context["exact_error"] == "connection timed out"
    assert context["next_recommended_question"] == "Can you access the internet when you are not connected to the VPN?"
    assert resolution_session.query(AIResolutionMessage).count() == 3


def test_basic_assistance_can_be_escalated_to_assigned_team(
    resolution_client, resolution_session, monkeypatch
):
    resolution_session.get(Ticket, 1).ai_classification_confidence = 0.1
    resolution_session.commit()
    monkeypatch.setattr(
        "routers.ai_resolution.AIResolutionService",
        lambda: pytest.fail("basic assistance must not create a provider"),
    )
    resolution_client.post("/api/tickets/1/ai-resolution/start")

    response = resolution_client.post("/api/tickets/1/ai-resolution/escalate")

    assert response.status_code == 200
    assert response.json()["status"] == "ESCALATED"
    assert response.json()["escalation_reason"] == "EMPLOYEE_REQUESTED_HUMAN_SUPPORT"


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


def test_provider_disabled_escalates_without_external_call(
    resolution_client, resolution_session, monkeypatch
):
    monkeypatch.setenv("GROQ_DATA_PROCESSING_APPROVED", "false")
    monkeypatch.setenv("GROQ_API_KEY", "test-only-not-a-real-key")

    response = resolution_client.post("/api/tickets/1/ai-resolution/start")

    assert response.status_code == 200
    assert response.json()["mode"] == "GUIDED"
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
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["mode"] == "BASIC"
    assert response.json()["eligibility_reason"] == "AI_CONFIGURATION_INVALID"
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


def test_basic_conversation_cannot_resolve_ticket(resolution_client, resolution_session):
    resolution_session.get(Ticket, 1).ai_classification_confidence = 0.1
    resolution_session.commit()
    resolution_client.post("/api/tickets/1/ai-resolution/start")

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


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        ("get", "/api/tickets/1/ai-resolution", None),
        ("post", "/api/tickets/1/ai-resolution/start", None),
        ("post", "/api/tickets/1/ai-resolution/messages", {"body": "Update"}),
        ("post", "/api/tickets/1/ai-resolution/escalate", None),
    ],
)
def test_every_conversation_endpoint_requires_ticket_ownership(
    resolution_client, resolution_session, method, path, json_body
):
    app.dependency_overrides[get_current_user] = lambda: resolution_session.get(User, 2)

    if method == "get":
        response = resolution_client.get(path)
    else:
        response = resolution_client.post(path, json=json_body)

    assert response.status_code == 403


@pytest.mark.parametrize("action", ["start", "messages"])
def test_resolved_ticket_rejects_troubleshooting_actions(resolution_client, resolution_session, action):
    ticket = resolution_session.get(Ticket, 1)
    ticket.status = TicketStatus.RESOLVED
    resolution_session.commit()
    if action == "start":
        response = resolution_client.post("/api/tickets/1/ai-resolution/start")
    else:
        # Create an active conversation first, then resolve the ticket.
        conversation = AIResolutionConversation(ticket_id=1, status="ACTIVE")
        resolution_session.add(conversation)
        resolution_session.commit()
        response = resolution_client.post(
            "/api/tickets/1/ai-resolution/messages",
            json={"body": "I still need help"},
        )

    assert response.status_code == 409
    assert "already resolved" in response.json()["detail"]
