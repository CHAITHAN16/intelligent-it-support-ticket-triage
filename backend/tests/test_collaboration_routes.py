import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base, Comment, Ticket, TicketStatus, User, UserRole


@pytest.fixture
def database_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    # PostgreSQL supplies the identity value for comments; provide that value
    # in this SQLite-only test fixture without changing the production model.
    def assign_comment_id(db_session, flush_context, instances):
        next_id = 1
        for comment in db_session.new:
            if isinstance(comment, Comment):
                comment.id = next_id
                next_id += 1

    event.listen(Session, "before_flush", assign_comment_id)
    session.add(User(id=1, name="Test Agent", email="agent@test.local", role=UserRole.SUPPORT_AGENT))
    session.add(
        Ticket(
            id=1,
            title="VPN issue",
            description="The VPN is unavailable.",
            priority="MEDIUM",
            status=TicketStatus.NEW,
            creator_id=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    yield session
    event.remove(Session, "before_flush", assign_comment_id)
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


def test_create_comment(client):
    response = client.post("/api/tickets/1/comments", json={"author_id": 1, "body": "  Investigating the VPN configuration.  "})

    assert response.status_code == 201
    assert response.json()["body"] == "Investigating the VPN configuration."
    assert response.json()["ticket_id"] == 1
    assert response.json()["author_id"] == 1


@pytest.mark.parametrize("body", ["", "   "])
def test_reject_empty_comment(client, body):
    assert client.post("/api/tickets/1/comments", json={"author_id": 1, "body": body}).status_code == 422


def test_comment_for_nonexistent_ticket_returns_404(client):
    response = client.post("/api/tickets/999/comments", json={"author_id": 1, "body": "Hello"})

    assert response.status_code == 404


def test_comments_are_listed_oldest_first(client):
    client.post("/api/tickets/1/comments", json={"author_id": 1, "body": "First"})
    client.post("/api/tickets/1/comments", json={"author_id": 1, "body": "Second"})

    response = client.get("/api/tickets/1/comments")

    assert response.status_code == 200
    assert [comment["body"] for comment in response.json()] == ["First", "Second"]


def test_initial_status_change_creates_history(client):
    response = client.patch("/api/tickets/1", json={"status": "IN_PROGRESS"})

    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"
    history = client.get("/api/tickets/1/history").json()
    assert len(history) == 1
    assert history[0]["old_status"] == "NEW"
    assert history[0]["new_status"] == "IN_PROGRESS"


def test_multiple_status_changes_create_multiple_records(client):
    client.patch("/api/tickets/1", json={"status": "IN_PROGRESS"})
    client.patch("/api/tickets/1", json={"status": "RESOLVED"})
    client.patch("/api/tickets/1", json={"status": "CLOSED"})

    history = client.get("/api/tickets/1/history").json()
    assert [(item["old_status"], item["new_status"]) for item in history] == [
        ("NEW", "IN_PROGRESS"),
        ("IN_PROGRESS", "RESOLVED"),
        ("RESOLVED", "CLOSED"),
    ]


def test_unchanged_status_creates_no_history(client):
    response = client.patch("/api/tickets/1", json={"status": "NEW"})

    assert response.status_code == 200
    assert client.get("/api/tickets/1/history").json() == []


def test_history_is_chronological(client):
    client.patch("/api/tickets/1", json={"status": "IN_PROGRESS"})
    client.patch("/api/tickets/1", json={"status": "RESOLVED"})

    history = client.get("/api/tickets/1/history").json()
    timestamps = [item["changed_at"] for item in history]
    assert timestamps == sorted(timestamps)


def test_history_for_nonexistent_ticket_returns_404(client):
    assert client.get("/api/tickets/999/history").status_code == 404


def test_status_update_rolls_back_when_history_commit_fails(database_session):
    app.dependency_overrides[get_db] = lambda: database_session
    original_commit = database_session.commit

    def fail_commit():
        raise RuntimeError("history commit failed")

    database_session.commit = fail_commit
    try:
        with pytest.raises(RuntimeError, match="history commit failed"):
            from routers.tickets import update_ticket
            from schemas.tickets import TicketUpdateRequest

            update_ticket(1, TicketUpdateRequest(status=TicketStatus.IN_PROGRESS), database_session)
        database_session.rollback()
        assert database_session.get(Ticket, 1).status == TicketStatus.NEW
    finally:
        database_session.commit = original_commit
        app.dependency_overrides.clear()


def test_comment_creation_rolls_back_when_commit_fails(database_session):
    app.dependency_overrides[get_db] = lambda: database_session
    original_commit = database_session.commit

    def fail_commit():
        raise RuntimeError("comment commit failed")

    database_session.commit = fail_commit
    try:
        with pytest.raises(RuntimeError, match="comment commit failed"):
            from routers.collaboration import create_comment
            from schemas.collaboration import CommentCreate

            create_comment(1, CommentCreate(author_id=1, body="Temporary comment"), database_session)
        database_session.rollback()
        assert database_session.query(Comment).count() == 0
    finally:
        database_session.commit = original_commit
        app.dependency_overrides.clear()
