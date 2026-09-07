import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from auth import create_access_token, password_hash
from database import get_db
from main import app
from models import Base, Comment, Team, TeamMember, Ticket, TicketStatus, User, UserRole


@pytest.fixture
def database_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    next_id = {Comment: 1}

    def assign_ids(db_session, flush_context, instances):
        for comment in db_session.new:
            if isinstance(comment, Comment) and comment.id is None:
                comment.id = next_id[Comment]
                next_id[Comment] += 1

    event.listen(Session, "before_flush", assign_ids)
    employee = User(id=1, name="Employee One", email="employee@example.com", role=UserRole.EMPLOYEE, password_hash=password_hash.hash("employee-pass"))
    other_employee = User(id=2, name="Employee Two", email="other@example.com", role=UserRole.EMPLOYEE, password_hash=password_hash.hash("other-pass"))
    agent = User(id=3, name="Agent One", email="agent@example.com", role=UserRole.SUPPORT_AGENT, password_hash=password_hash.hash("agent-pass"))
    team = Team(id=1, name="Network Infrastructure")
    session.add_all([employee, other_employee, agent, team, TeamMember(team_id=1, user_id=3, member_role=UserRole.SUPPORT_AGENT)])
    now = datetime.now(timezone.utc)
    session.add_all([
        Ticket(id=1, title="Mine", description="Mine", creator_id=1, assigned_team_id=1, status=TicketStatus.NEW, created_at=now, updated_at=now),
        Ticket(id=2, title="Other", description="Other", creator_id=2, assigned_team_id=1, status=TicketStatus.NEW, created_at=now, updated_at=now),
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


def test_registration_and_duplicate_email(client):
    response = client.post("/api/auth/register", json={"name": "New User", "email": "new@example.com", "password": "secure-pass"})
    assert response.status_code == 201
    assert response.json()["role"] == "EMPLOYEE"
    assert client.post("/api/auth/register", json={"name": "Duplicate", "email": "NEW@example.com", "password": "secure-pass"}).status_code == 409


def test_login_success_and_password_failures(client):
    response = client.post("/api/auth/login", json={"email": "employee@example.com", "password": "employee-pass"})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == 1
    assert response.json()["access_token"]
    assert client.post("/api/auth/login", json={"email": "employee@example.com", "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "missing@example.com", "password": "wrong-pass"}).status_code == 401


def test_me_requires_and_returns_authenticated_user(client, database_session):
    assert client.get("/api/auth/me").status_code == 401
    response = client.get("/api/auth/me", headers=token_for(database_session, 1))
    assert response.status_code == 200
    assert response.json()["email"] == "employee@example.com"


def test_employee_ticket_access_is_scoped_and_identity_cannot_be_spoofed(client, database_session, monkeypatch):
    headers = token_for(database_session, 1)
    assert [ticket["id"] for ticket in client.get("/api/tickets", headers=headers).json()] == [1]
    assert client.get("/api/tickets/2", headers=headers).status_code == 403
    assert client.get("/api/tickets?creator_id=2", headers=headers).status_code == 403

    class Triage:
        category = "Network"
        subcategory = None
        priority = "MEDIUM"
        confidence = 0.9
        model_version = "test"

    monkeypatch.setattr("routers.tickets.TriageService.triage", lambda self, title, description: Triage())
    response = client.post(
        "/api/tickets",
        json={"title": "Identity test", "description": "Must belong to token user", "creator_id": 2},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["creator_id"] == 1


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
