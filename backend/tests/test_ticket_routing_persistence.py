import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from datetime import datetime, timezone

import pytest

from models import Ticket, TicketPriority, TicketStatus
from models import KnowledgeBaseArticle
from routers.tickets import _ticket_response, create_ticket
from schemas.tickets import TicketCreate


class InMemorySession:
    """Small session double for the HTTP-to-Celery handoff."""

    def __init__(self):
        self.added = []
        self.commit_called = False
        self.rollback_called = False
        self.next_ticket_id = 1

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commit_called = True
        for value in self.added:
            if isinstance(value, Ticket) and value.id is None:
                value.id = self.next_ticket_id
                self.next_ticket_id += 1
                now = datetime.now(timezone.utc)
                value.created_at = now
                value.updated_at = now

    def refresh(self, value):
        pass

    def rollback(self):
        self.rollback_called = True


@pytest.fixture(autouse=True)
def avoid_live_broker(monkeypatch):
    monkeypatch.setattr("routers.tickets.process_ticket.delay", lambda ticket_id: None)


def test_ticket_creation_persists_before_enqueue(monkeypatch):
    db = InMemorySession()
    queued_ticket_ids = []
    monkeypatch.setattr("routers.tickets.process_ticket.delay", queued_ticket_ids.append)

    ticket = create_ticket(
        TicketCreate(
            title="VPN connection keeps dropping",
            description="The company VPN disconnects repeatedly.",
            creator_id=1,
        ),
        db,
    )

    assert ticket.id == 1
    assert ticket.priority == TicketPriority.MEDIUM
    assert ticket.status == TicketStatus.NEW
    assert ticket.ai_predicted_category is None
    assert ticket.ai_predicted_priority is None
    assert ticket.assigned_team_id is None
    assert db.commit_called
    assert queued_ticket_ids == [ticket.id]
    assert not db.rollback_called


def test_enqueue_failure_does_not_rollback_ticket(monkeypatch):
    db = InMemorySession()

    def fail_enqueue(ticket_id):
        raise RuntimeError("Redis unavailable")

    monkeypatch.setattr("routers.tickets.process_ticket.delay", fail_enqueue)
    ticket = create_ticket(
        TicketCreate(title="Queue failure", description="Keep this ticket stored", creator_id=1),
        db,
    )

    assert ticket.id == 1
    assert db.commit_called
    assert not db.rollback_called


def test_ticket_response_derives_article_fields_without_mutating_ticket():
    article = KnowledgeBaseArticle(id=3, title="VPN guide", summary="Help", category="Network", resolution_steps="Reconnect.", keywords="vpn", active=True)

    class ResponseSession:
        def get(self, model, article_id):
            assert model is KnowledgeBaseArticle
            assert article_id == 3
            return article

    ticket = Ticket(
        id=8,
        title="VPN issue",
        description="VPN disconnects",
        creator_id=1,
        category="Network",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.NEW,
        knowledge_article_id=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    response = _ticket_response(ticket, ResponseSession())

    assert response.knowledge_article_title == "VPN guide"
    assert response.solution_source == "Prototype curated knowledge base: VPN guide"
    assert "knowledge_article_title" not in ticket.__dict__
    assert "solution_source" not in ticket.__dict__


@pytest.mark.parametrize(("confidence", "status", "suggested_solution", "article_id", "expected_status", "expected_level"), [
    (0.82, "MATCHED", "Try reconnecting.", 3, "MATCHED", "HIGH"),
    (0.55, "MATCHED", "Try reconnecting.", 3, "MATCHED", "MEDIUM"),
    (0.31, "MATCHED", "Try reconnecting.", 3, "NO_MATCH", "LOW"),
    (0.25, "NO_MATCH", None, None, "NO_MATCH", None),
])
def test_ticket_response_exposes_safe_confidence_level(confidence, status, suggested_solution, article_id, expected_status, expected_level):
    class ResponseSession:
        def get(self, model, article_id):
            return None

    ticket = Ticket(
        id=9,
        title="Wi-Fi issue",
        description="Wireless issue",
        creator_id=1,
        category="Network",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.NEW,
        solution_status=status,
        suggested_solution=suggested_solution,
        knowledge_article_id=article_id,
        solution_confidence=confidence,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    response = _ticket_response(ticket, ResponseSession())

    assert response.solution_status == expected_status
    assert response.solution_confidence == confidence
    assert response.solution_confidence_level == expected_level
    if expected_status == "NO_MATCH":
        assert response.suggested_solution is None
        assert response.knowledge_article_id is None
        assert response.knowledge_article_title is None
        assert response.solution_source is None


def test_low_confidence_response_does_not_mutate_ticket():
    ticket = Ticket(
        id=10,
        title="Wi-Fi issue",
        description="Wireless issue",
        creator_id=1,
        category="Network",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.NEW,
        solution_status="MATCHED",
        suggested_solution="Try reconnecting.",
        knowledge_article_id=3,
        solution_confidence=0.31,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    class ResponseSession:
        def get(self, model, article_id):
            raise AssertionError("must not fetch the article for a low-confidence match")

    response = _ticket_response(ticket, ResponseSession())

    assert response.solution_status == "NO_MATCH"
    assert ticket.solution_status == "MATCHED"
    assert ticket.suggested_solution == "Try reconnecting."
    assert ticket.knowledge_article_id == 3
