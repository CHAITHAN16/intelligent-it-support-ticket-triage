import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import create_access_token, get_current_user
from database import get_db
from main import app
from models import Base, SLATarget, Team, TeamMember, Ticket, TicketPriority, TicketStatus, User, UserRole


@pytest.fixture
def operations_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    admin = User(id=1, name="Admin", email="admin@ops.test", role=UserRole.ADMIN)
    agent_one = User(id=2, name="Agent One", email="one@ops.test", role=UserRole.SUPPORT_AGENT)
    agent_two = User(id=3, name="Agent Two", email="two@ops.test", role=UserRole.SUPPORT_AGENT)
    agent_three = User(id=4, name="Agent Three", email="three@ops.test", role=UserRole.SUPPORT_AGENT)
    employee = User(id=5, name="Employee", email="employee@ops.test", role=UserRole.EMPLOYEE)
    team_one = Team(id=1, name="Network")
    team_two = Team(id=2, name="Security")
    session.add_all([
        admin, agent_one, agent_two, agent_three, employee, team_one, team_two,
        TeamMember(team_id=1, user_id=2, member_role=UserRole.SUPPORT_AGENT),
        TeamMember(team_id=2, user_id=2, member_role=UserRole.SUPPORT_AGENT),
        TeamMember(team_id=2, user_id=3, member_role=UserRole.SUPPORT_AGENT),
        SLATarget(priority=TicketPriority.LOW, response_minutes=60, resolution_minutes=240),
        SLATarget(priority=TicketPriority.MEDIUM, response_minutes=10, resolution_minutes=30),
        SLATarget(priority=TicketPriority.HIGH, response_minutes=60, resolution_minutes=240),
        SLATarget(priority=TicketPriority.URGENT, response_minutes=60, resolution_minutes=240),
        Ticket(id=1, title="Near response deadline", description="Private body", creator_id=5, assigned_team_id=1, priority=TicketPriority.HIGH, status=TicketStatus.NEW, created_at=now - timedelta(minutes=30), updated_at=now - timedelta(minutes=30)),
        Ticket(id=2, title="Breached response", description="Private body", creator_id=5, assigned_team_id=1, priority=TicketPriority.MEDIUM, status=TicketStatus.IN_PROGRESS, created_at=now - timedelta(minutes=20), updated_at=now - timedelta(minutes=20)),
        Ticket(id=3, title="Historical breaches", description="Private body", creator_id=5, assigned_team_id=1, priority=TicketPriority.HIGH, status=TicketStatus.RESOLVED, created_at=now - timedelta(minutes=500), updated_at=now - timedelta(minutes=100), resolved_at=now - timedelta(minutes=100)),
        Ticket(id=4, title="Other team ticket", description="Private body", creator_id=5, assigned_team_id=2, priority=TicketPriority.URGENT, status=TicketStatus.IN_PROGRESS, created_at=now - timedelta(minutes=200), updated_at=now - timedelta(minutes=200)),
    ])
    session.commit()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, session, now
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def headers(session, user_id: int):
    return {"Authorization": f"Bearer {create_access_token(session.get(User, user_id))}"}


def test_team_agents_are_membership_scoped_and_include_team_memberships(operations_client):
    client, session, _ = operations_client
    agent = headers(session, 2)
    admin = headers(session, 1)

    assert client.get("/api/teams/2/agents", headers=agent).status_code == 200
    forbidden = client.get("/api/teams/1/agents", headers=headers(session, 3))
    assert forbidden.status_code == 403
    agents = client.get("/api/teams/1/agents", headers=admin)
    assert agents.status_code == 200
    assert agents.json() == [{
        "id": 2,
        "name": "Agent One",
        "memberships": [{"team_id": 1, "team_name": "Network"}, {"team_id": 2, "team_name": "Security"}],
    }]
    assert client.get("/api/teams/1/agents", headers=headers(session, 5)).status_code == 403
    assert client.get("/api/teams/999/agents", headers=admin).status_code == 404


def test_sla_overview_scope_approaching_breaches_and_priority_counts(operations_client):
    client, session, _ = operations_client
    response = client.get("/api/sla/overview?team_id=1", headers=headers(session, 2))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_tickets"] == 3
    assert [item["ticket_id"] for item in body["approaching_response"]] == [1]
    assert [item["ticket_id"] for item in body["approaching_resolution"]] == [2]
    assert {item["ticket_id"] for item in body["breached_response"]} == {2, 3}
    assert [item["ticket_id"] for item in body["breached_resolution"]] == [3]
    assert next(item for item in body["breached_response"] if item["ticket_id"] == 2)["actively_overdue"] is True
    historical = next(item for item in body["breached_resolution"] if item["ticket_id"] == 3)
    assert historical["actively_overdue"] is False
    assert historical["resolution"]["state"] == "BREACHED"
    counts = {item["priority"]: item for item in body["priority_counts"]}
    assert counts["HIGH"]["tickets"] == 2
    assert counts["HIGH"]["breached_resolution"] == 1
    assert counts["MEDIUM"]["breached_response"] == 1

    other_team = client.get("/api/sla/overview?team_id=2", headers=headers(session, 1))
    assert other_team.status_code == 200
    assert [item["ticket_id"] for item in other_team.json()["breached_response"]] == [4]
    assert client.get("/api/sla/overview?team_id=2", headers=headers(session, 2)).status_code == 200
    assert client.get("/api/sla/overview?team_id=1&priority=URGENT", headers=headers(session, 2)).json()["total_tickets"] == 0
    assert client.get("/api/sla/overview?state=BREACHED", headers=headers(session, 2)).json()["total_tickets"] == 3
    assert client.get("/api/sla/overview?team_id=2", headers=headers(session, 3)).status_code == 200
    assert client.get("/api/sla/overview?team_id=1", headers=headers(session, 3)).status_code == 403


def test_sla_ticket_detail_states_and_filters_hide_unavailable_tickets(operations_client):
    client, session, _ = operations_client
    agent = headers(session, 2)
    detail = client.get("/api/sla/tickets/1?team_id=1", headers=agent)
    assert detail.status_code == 200
    body = detail.json()
    assert body["response"]["target_minutes"] == 60
    assert body["response"]["state"] == "APPROACHING"
    assert body["response"]["remaining_seconds"] > 0
    assert body["response"]["completed_at"] is None
    assert body["resolution"]["target_minutes"] == 240
    assert body["resolution"]["state"] == "ON_TRACK"
    assert body["actively_overdue"] is False
    assert "description" not in body
    assert client.get("/api/sla/tickets/1", headers=headers(session, 3)).status_code == 404
    assert client.get("/api/sla/tickets/1?priority=URGENT", headers=agent).status_code == 404
    assert client.get("/api/sla/tickets/1?state=BREACHED", headers=agent).status_code == 404


def test_ticket_sla_exposes_recorded_first_response_as_completed_clock(operations_client):
    client, session, now = operations_client
    ticket = session.get(Ticket, 1)
    ticket.first_response_at = now - timedelta(minutes=5)
    session.commit()

    response = client.get("/api/sla/tickets/1", headers=headers(session, 2))
    assert response.status_code == 200
    clock = response.json()["response"]
    assert clock["state"] == "MET"
    assert clock["completed_at"] is not None
    assert clock["remaining_seconds"] is None
    assert clock["overdue_seconds"] is None
    assert response.json()["created_at"].endswith("Z")


def test_admin_sees_all_tickets_and_terminal_slas_are_not_actively_overdue(operations_client):
    client, session, _ = operations_client
    response = client.get("/api/sla/overview", headers=headers(session, 1))
    assert response.status_code == 200
    assert response.json()["total_tickets"] == 4
    closed = client.get("/api/sla/tickets/3", headers=headers(session, 1)).json()
    assert closed["status"] == "RESOLVED"
    assert closed["resolution"]["state"] == "BREACHED"
    assert closed["resolution"]["actively_overdue"] is False
    assert closed["actively_overdue"] is False
    resolved_ticket = session.get(Ticket, 3)
    resolved_ticket.status = TicketStatus.CLOSED
    session.commit()
    closed_detail = client.get("/api/sla/tickets/3", headers=headers(session, 1)).json()
    assert closed_detail["status"] == "CLOSED"
    assert closed_detail["resolution"]["state"] == "BREACHED"
    assert closed_detail["actively_overdue"] is False


def test_empty_team_dataset_and_employee_authorization(operations_client):
    client, session, _ = operations_client
    # Agent Three has no team membership, so the overview is a valid empty result.
    response = client.get("/api/sla/overview", headers=headers(session, 4))
    assert response.status_code == 200
    assert response.json()["total_tickets"] == 0
    assert response.json()["approaching_response"] == []
    assert all(count["tickets"] == 0 for count in response.json()["priority_counts"])
    assert client.get("/api/sla/overview", headers=headers(session, 5)).status_code == 403
    assert client.get("/api/sla/tickets/1", headers=headers(session, 5)).status_code == 403


def test_state_and_approach_window_query_validation(operations_client):
    client, session, _ = operations_client
    admin = headers(session, 1)
    assert client.get("/api/sla/overview?state=UNKNOWN", headers=admin).status_code == 422
    assert client.get("/api/sla/overview?approaching_within_minutes=0", headers=admin).status_code == 422
    response = client.get("/api/sla/overview?priority=HIGH&approaching_within_minutes=15", headers=admin)
    assert response.status_code == 200
    assert response.json()["total_tickets"] == 2
