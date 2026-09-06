import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base, Team, Ticket, TicketPriority, TicketStatus
from routers.teams import list_team_tickets


@pytest.fixture(scope="module")
def database_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    teams = [
        Team(id=1, name="Network Infrastructure"),
        Team(id=2, name="Security Operations"),
        Team(id=3, name="Software Support"),
        Team(id=4, name="General IT Support"),
    ]
    session.add_all(teams)
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session.add_all(
        [
            Ticket(
                id=1,
                title="Network outage",
                description="The office network is unavailable.",
                category="Network",
                priority=TicketPriority.HIGH,
                status=TicketStatus.NEW,
                creator_id=1,
                assigned_team_id=1,
                ai_predicted_category="Network",
                ai_predicted_priority=TicketPriority.HIGH,
                ai_confidence=0.9,
                ai_model_version="category-v1+priority-v2",
                created_at=base_time,
                updated_at=base_time,
            ),
            Ticket(
                id=2,
                title="VPN latency",
                description="The VPN is slow.",
                category="Network",
                priority=TicketPriority.LOW,
                status=TicketStatus.IN_PROGRESS,
                creator_id=1,
                assigned_team_id=1,
                ai_predicted_category="Network",
                ai_predicted_priority=TicketPriority.LOW,
                ai_confidence=0.8,
                ai_model_version="category-v1+priority-v2",
                created_at=base_time + timedelta(days=1),
                updated_at=base_time + timedelta(days=1),
            ),
            Ticket(
                id=3,
                title="Security alert",
                description="A suspicious login was detected.",
                category="Security",
                priority=TicketPriority.URGENT,
                status=TicketStatus.RESOLVED,
                creator_id=1,
                assigned_team_id=2,
                ai_predicted_category="Security",
                ai_predicted_priority=TicketPriority.URGENT,
                ai_confidence=0.95,
                ai_model_version="category-v1+priority-v2",
                created_at=base_time + timedelta(days=2),
                updated_at=base_time + timedelta(days=2),
            ),
            Ticket(
                id=4,
                title="Application defect",
                description="The application fails to load.",
                category="Software",
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.CLOSED,
                creator_id=1,
                assigned_team_id=3,
                ai_predicted_category="Software",
                ai_predicted_priority=TicketPriority.MEDIUM,
                ai_confidence=0.85,
                ai_model_version="category-v1+priority-v2",
                created_at=base_time + timedelta(days=3),
                updated_at=base_time + timedelta(days=3),
            ),
        ]
    )
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(database_session):
    def override_get_db():
        yield database_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_lists_existing_teams(client):
    response = client.get("/api/teams")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 4, "name": "General IT Support"},
        {"id": 1, "name": "Network Infrastructure"},
        {"id": 2, "name": "Security Operations"},
        {"id": 3, "name": "Software Support"},
    ]


@pytest.mark.parametrize(
    ("team_id", "expected_category"),
    [(1, "Network"), (2, "Security"), (3, "Software"), (4, None)],
)
def test_team_queue_is_isolated(client, team_id, expected_category):
    response = client.get(f"/api/teams/{team_id}/tickets")

    assert response.status_code == 200
    tickets = response.json()
    assert all(ticket["assigned_team_id"] == team_id for ticket in tickets)
    if expected_category is None:
        assert tickets == []
    else:
        assert all(ticket["category"] == expected_category for ticket in tickets)


def test_filters_are_applied(client):
    assert [ticket["id"] for ticket in client.get("/api/teams/1/tickets?status=NEW").json()] == [1]
    assert [ticket["id"] for ticket in client.get("/api/teams/1/tickets?priority=LOW").json()] == [2]
    assert [ticket["id"] for ticket in client.get("/api/teams/1/tickets?category=Network").json()] == [2, 1]


@pytest.mark.parametrize(
    ("sort", "expected_ids"),
    [("newest", [2, 1]), ("oldest", [1, 2]), ("priority", [1, 2])],
)
def test_supported_sorting(client, sort, expected_ids):
    response = client.get(f"/api/teams/1/tickets?sort={sort}")

    assert response.status_code == 200
    assert [ticket["id"] for ticket in response.json()] == expected_ids


@pytest.mark.parametrize(
    "query",
    ["status=INVALID", "priority=INVALID", "category=", "sort=recent"],
)
def test_invalid_filters_return_422(client, query):
    assert client.get(f"/api/teams/1/tickets?{query}").status_code == 422


def test_nonexistent_team_returns_404(client):
    response = client.get("/api/teams/999/tickets")

    assert response.status_code == 404


def test_direct_query_is_team_scoped(database_session):
    tickets = list_team_tickets(
        1,
        status=None,
        priority=None,
        category=None,
        sort="newest",
        db=database_session,
    )

    assert tickets
    assert all(ticket.assigned_team_id == 1 for ticket in tickets)
