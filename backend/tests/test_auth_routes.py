import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from auth import create_access_token, password_hash, verify_password
from database import get_db
from main import app
from models import AssignmentSource, Base, Comment, SLATarget, Team, TeamMember, Ticket, TicketAssignment, TicketFieldHistory, TicketFirstResponse, TicketPriority, TicketStatus, TicketStatusHistory, User, UserRole


@pytest.fixture
def database_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    next_id = {Comment: 1, Ticket: 4, TicketAssignment: 1, TicketFieldHistory: 1, TicketStatusHistory: 1, User: 4}

    def assign_ids(db_session, flush_context, instances):
        for comment in db_session.new:
            if isinstance(comment, Comment) and comment.id is None:
                comment.id = next_id[Comment]
                next_id[Comment] += 1
            if isinstance(comment, TicketStatusHistory) and comment.id is None:
                comment.id = next_id[TicketStatusHistory]
                next_id[TicketStatusHistory] += 1
            if isinstance(comment, TicketFieldHistory) and comment.id is None:
                comment.id = next_id[TicketFieldHistory]
                next_id[TicketFieldHistory] += 1
            if isinstance(comment, TicketAssignment) and comment.id is None:
                comment.id = next_id[TicketAssignment]
                next_id[TicketAssignment] += 1
            if isinstance(comment, User) and comment.id is None:
                comment.id = next_id[User]
                next_id[User] += 1
            if isinstance(comment, Ticket) and comment.id is None:
                comment.id = next_id[Ticket]
                next_id[Ticket] += 1

    event.listen(Session, "before_flush", assign_ids)
    employee = User(id=1, name="Employee One", email="employee@example.com", role=UserRole.EMPLOYEE, password_hash=password_hash.hash("employee-pass"))
    other_employee = User(id=2, name="Employee Two", email="other@example.com", role=UserRole.EMPLOYEE, password_hash=password_hash.hash("other-pass"))
    agent = User(id=3, name="Agent One", email="agent@example.com", role=UserRole.SUPPORT_AGENT, password_hash=password_hash.hash("agent-pass"))
    team = Team(id=1, name="Network Infrastructure")
    other_team = Team(id=2, name="Security Operations")
    session.add_all([
        employee,
        other_employee,
        agent,
        team,
        other_team,
        TeamMember(team_id=1, user_id=3, member_role=UserRole.SUPPORT_AGENT),
    ])
    now = datetime.now(timezone.utc)
    session.add_all([
        Ticket(id=1, title="Mine", description="Mine", creator_id=1, assigned_team_id=1, status=TicketStatus.NEW, routing_reason="AI category 'Network' routed to Network Infrastructure", created_at=now, updated_at=now),
        Ticket(id=2, title="Other", description="Other", creator_id=2, assigned_team_id=1, status=TicketStatus.NEW, created_at=now, updated_at=now),
        Ticket(id=3, title="Other team", description="Other team", creator_id=2, assigned_team_id=2, status=TicketStatus.NEW, created_at=now, updated_at=now),
    ])
    session.commit()
    yield session
    event.remove(Session, "before_flush", assign_ids)
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(database_session):
    app.dependency_overrides[get_db] = lambda: database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def token_for(database_session, user_id):
    return {"Authorization": f"Bearer {create_access_token(database_session.get(User, user_id))}"}


def test_registration_persists_an_employee_with_the_client_payload(client, database_session):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test Employee",
            "email": "employee@test.com",
            "password": "Test@12345",
            "role": "employee",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": 4,
        "name": "Test Employee",
        "email": "employee@test.com",
        "role": "EMPLOYEE",
        "active": True,
    }

    registered_user = database_session.get(User, body["id"])
    assert registered_user is not None
    assert registered_user.password_hash != "Test@12345"
    assert verify_password("Test@12345", registered_user.password_hash)


def test_registration_rejects_duplicate_email(client):
    response = client.post("/api/auth/register", json={"name": "New User", "email": "new@example.com", "password": "secure-pass"})
    assert response.status_code == 201
    assert response.json()["role"] == "EMPLOYEE"
    assert client.post("/api/auth/register", json={"name": "Duplicate", "email": "NEW@example.com", "password": "secure-pass"}).status_code == 409


def test_login_normalizes_email_case(client):
    response = client.post("/api/auth/login", json={"email": "EMPLOYEE@EXAMPLE.COM", "password": "employee-pass"})

    assert response.status_code == 200
    assert response.json()["user"]["id"] == 1


def test_login_success_and_password_failures(client):
    response = client.post("/api/auth/login", json={"email": "employee@example.com", "password": "employee-pass"})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == 1
    assert response.json()["access_token"]
    assert client.post("/api/auth/login", json={"email": "employee@example.com", "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "missing@example.com", "password": "wrong-pass"}).status_code == 401


def test_login_with_malformed_stored_hash_returns_invalid_credentials(client, database_session):
    database_session.get(User, 1).password_hash = "legacy-plaintext-password"
    database_session.commit()

    response = client.post("/api/auth/login", json={"email": "employee@example.com", "password": "employee-pass"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_requires_and_returns_authenticated_user(client, database_session):
    assert client.get("/api/auth/me").status_code == 401
    response = client.get("/api/auth/me", headers=token_for(database_session, 1))
    assert response.status_code == 200
    assert response.json()["email"] == "employee@example.com"


def test_ticket_creation_requires_authentication(client):
    response = client.post(
        "/api/tickets",
        json={"title": "Unauthenticated", "description": "Should not be created", "creator_id": 1},
    )

    assert response.status_code == 401


def test_ticket_response_includes_persisted_routing_reason(client, database_session):
    response = client.get("/api/tickets/1", headers=token_for(database_session, 1))

    assert response.status_code == 200
    assert response.json()["routing_reason"] == "AI category 'Network' routed to Network Infrastructure"


def test_employee_ticket_access_is_scoped_and_identity_cannot_be_spoofed(client, database_session, monkeypatch):
    headers = token_for(database_session, 1)
    assert [ticket["id"] for ticket in client.get("/api/tickets", headers=headers).json()] == [1]
    assert client.get("/api/tickets/2", headers=headers).status_code == 403
    assert client.get("/api/tickets?creator_id=2", headers=headers).status_code == 403
    assert client.patch("/api/tickets/2", json={"status": "IN_PROGRESS"}, headers=headers).status_code == 403

    queued_ticket_ids = []
    monkeypatch.setattr("routers.tickets.process_ticket.delay", queued_ticket_ids.append)
    response = client.post(
        "/api/tickets",
        json={"title": "Identity test", "description": "Must belong to token user", "creator_id": 2},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["creator_id"] == 1
    assert database_session.get(Ticket, response.json()["id"]).creator_id == 1
    assert queued_ticket_ids == [response.json()["id"]]


def test_ticket_remains_persisted_when_enqueue_fails(client, database_session, monkeypatch):
    def fail_enqueue(ticket_id):
        raise RuntimeError("Redis unavailable")

    monkeypatch.setattr("routers.tickets.process_ticket.delay", fail_enqueue)
    response = client.post(
        "/api/tickets",
        json={"title": "Queue failure", "description": "The ticket must remain durable"},
        headers=token_for(database_session, 1),
    )

    assert response.status_code == 201
    ticket = database_session.get(Ticket, response.json()["id"])
    assert ticket is not None
    assert ticket.ai_predicted_category is None
    assert ticket.ai_predicted_priority is None
    assert ticket.assigned_team_id is None


def test_agent_authorization_and_comment_author_identity(client, database_session):
    agent_headers = token_for(database_session, 3)
    employee_headers = token_for(database_session, 1)
    assert client.get("/api/teams/1/tickets", headers=agent_headers).status_code == 200
    assert client.patch("/api/tickets/1", json={"status": "IN_PROGRESS"}, headers=agent_headers).status_code == 200
    assert client.post(
        "/api/tickets/1/comments",
        json={"author_id": 1, "body": "Working on it"},
        headers=agent_headers,
    ).json()["author_id"] == 3
    assert client.post(
        "/api/tickets/1/comments",
        json={"author_id": 1, "body": "Employee cannot create"},
        headers=employee_headers,
    ).status_code == 403
    assert client.get("/api/tickets/1/history", headers=employee_headers).status_code == 200


def test_agent_ticket_list_is_limited_to_member_teams(client, database_session):
    response = client.get("/api/tickets", headers=token_for(database_session, 3))

    assert response.status_code == 200
    assert sorted(ticket["id"] for ticket in response.json()) == [1, 2]
    assert client.get("/api/tickets/3", headers=token_for(database_session, 3)).status_code == 403
    assert client.patch(
        "/api/tickets/3",
        json={"status": "IN_PROGRESS"},
        headers=token_for(database_session, 3),
    ).status_code == 403
    assert client.post(
        "/api/tickets/3/comments",
        json={"body": "Not my team"},
        headers=token_for(database_session, 3),
    ).status_code == 403


def test_agent_field_overrides_are_audited_with_old_new_values_and_actor(client, database_session):
    response = client.patch(
        "/api/tickets/1",
        json={"category": "Network", "subcategory": "VPN", "priority": "HIGH"},
        headers=token_for(database_session, 3),
    )

    assert response.status_code == 200
    history = client.get("/api/tickets/1/field-history", headers=token_for(database_session, 3))
    assert history.status_code == 200
    assert [(entry["field_name"], entry["old_value"], entry["new_value"], entry["changed_by_id"]) for entry in history.json()] == [
        ("category", None, "Network", 3),
        ("subcategory", None, "VPN", 3),
        ("priority", "MEDIUM", "HIGH", 3),
    ]


def test_employee_cannot_create_field_or_team_overrides(client, database_session):
    response = client.patch(
        "/api/tickets/1",
        json={"category": "Security", "assigned_team_id": 2},
        headers=token_for(database_session, 1),
    )

    assert response.status_code == 403
    assert database_session.query(TicketFieldHistory).count() == 0
    assert database_session.query(TicketAssignment).count() == 0


def test_employee_cannot_resolve_ticket(client, database_session):
    response = client.patch(
        "/api/tickets/1",
        json={"status": "RESOLVED", "resolution_note": "The reported issue was fixed and verified."},
        headers=token_for(database_session, 1),
    )

    assert response.status_code == 403
    assert database_session.get(Ticket, 1).status == TicketStatus.NEW
    assert database_session.query(TicketStatusHistory).count() == 0


def test_agent_team_reassignment_closes_active_assignment_and_records_human_source(client, database_session):
    database_session.add(TeamMember(team_id=2, user_id=3, member_role=UserRole.SUPPORT_AGENT))
    database_session.add(
        TicketAssignment(
            ticket_id=1,
            team_id=1,
            source=AssignmentSource.AI,
            routing_reason="AI route",
        )
    )
    database_session.commit()

    response = client.patch("/api/tickets/1", json={"assigned_team_id": 2}, headers=token_for(database_session, 3))

    assert response.status_code == 200
    ticket = database_session.get(Ticket, 1)
    assert ticket.assigned_team_id == 2
    assert ticket.assigned_agent_id is None
    assignments = database_session.query(TicketAssignment).order_by(TicketAssignment.id).all()
    assert assignments[0].unassigned_at is not None
    assert assignments[1].source == AssignmentSource.HUMAN
    assert assignments[1].team_id == 2
    assert assignments[1].assigned_by_id == 3
    history = client.get("/api/tickets/1/assignments", headers=token_for(database_session, 3))
    assert [entry["source"] for entry in history.json()] == ["AI", "HUMAN"]


def test_agent_assignment_reassignment_and_safe_unassignment_are_audited(client, database_session):
    second_agent = User(id=4, name="Agent Two", email="agent2@example.com", role=UserRole.SUPPORT_AGENT)
    database_session.add_all([second_agent, TeamMember(team_id=1, user_id=4, member_role=UserRole.SUPPORT_AGENT)])
    database_session.commit()

    first = client.patch("/api/tickets/1", json={"assigned_agent_id": 3, "assignment_reason": "Initial owner"}, headers=token_for(database_session, 3))
    assert first.status_code == 200, first.text
    assert first.json()["assigned_team_id"] == 1
    assert first.json()["assigned_agent_id"] == 3

    second = client.patch("/api/tickets/1", json={"assigned_agent_id": 4, "assignment_reason": "Shift handoff"}, headers=token_for(database_session, 3))
    assert second.status_code == 200
    assert second.json()["assigned_agent_id"] == 4

    third = client.patch("/api/tickets/1", json={"assigned_agent_id": None, "assignment_reason": "Back to team queue"}, headers=token_for(database_session, 3))
    assert third.status_code == 200
    assert third.json()["assigned_agent_id"] is None
    assert third.json()["assigned_team_id"] == 1

    history = client.get("/api/tickets/1/assignments", headers=token_for(database_session, 3))
    assert history.status_code == 200
    rows = history.json()
    assert [(row["previous_agent_id"], row["agent_id"], row["assigned_by_id"], row["reason"]) for row in rows] == [
        (None, 3, 3, "Initial owner"),
        (3, 4, 3, "Shift handoff"),
        (4, None, 3, "Back to team queue"),
    ]
    assert all(row["assigned_at"] and row["unassigned_at"] for row in rows[:-1])
    assert rows[-1]["unassigned_at"] is None


def test_agent_cannot_assign_outside_own_team_or_to_nonmember(client, database_session):
    outsider = User(id=4, name="Outsider", email="outsider@example.com", role=UserRole.SUPPORT_AGENT)
    database_session.add(outsider)
    database_session.commit()

    assert client.patch("/api/tickets/1", json={"assigned_team_id": 2}, headers=token_for(database_session, 3)).status_code == 403
    assert client.patch("/api/tickets/1", json={"assigned_agent_id": 4}, headers=token_for(database_session, 3)).status_code == 422
    assert database_session.query(TicketAssignment).count() == 0


def test_employee_cannot_assign_an_agent(client, database_session):
    assert client.patch("/api/tickets/1", json={"assigned_agent_id": 3}, headers=token_for(database_session, 1)).status_code == 403
    assert database_session.query(TicketAssignment).count() == 0


def test_authorized_agent_comment_creates_only_new_first_response_event(client, database_session):
    # Existing comments have no visibility/event classification and must not be backfilled.
    database_session.add(Comment(id=1, ticket_id=1, author_id=1, body="Historic customer note"))
    database_session.commit()
    assert database_session.get(Ticket, 1).first_response_at is None
    assert database_session.query(TicketFirstResponse).count() == 0

    response = client.post("/api/tickets/1/comments", json={"body": "Agent response"}, headers=token_for(database_session, 3))
    assert response.status_code == 201
    event_row = database_session.query(TicketFirstResponse).one()
    assert event_row.ticket_id == 1
    assert event_row.comment_id == response.json()["id"]
    assert event_row.agent_id == 3
    assert database_session.get(Ticket, 1).first_response_at is not None


def test_sla_target_configuration_is_admin_only_and_validated(client, database_session):
    employee_headers = token_for(database_session, 1)
    agent_headers = token_for(database_session, 3)
    assert client.put("/api/sla/targets/HIGH", json={"response_minutes": 30, "resolution_minutes": 120}, headers=agent_headers).status_code == 403
    assert client.put("/api/sla/targets/HIGH", json={"response_minutes": 120, "resolution_minutes": 60}, headers=token_for(database_session, 1)).status_code == 403

    admin = User(id=5, name="Admin", email="admin@example.com", role=UserRole.ADMIN)
    database_session.add(admin)
    database_session.commit()
    updated = client.put("/api/sla/targets/HIGH", json={"response_minutes": 30, "resolution_minutes": 120}, headers=token_for(database_session, 5))
    assert updated.status_code == 200, updated.text
    assert updated.json()["priority"] == "HIGH"
    assert updated.json()["response_minutes"] == 30
    assert updated.json()["resolution_minutes"] == 120
    invalid = client.put("/api/sla/targets/HIGH", json={"response_minutes": 120, "resolution_minutes": 60}, headers=token_for(database_session, 5))
    assert invalid.status_code == 422
    assert database_session.get(SLATarget, TicketPriority.HIGH).response_minutes == 30
