import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import SessionLocal
from models import AssignmentSource, Base, KnowledgeBaseArticle, Team, Ticket, TicketAssignment, TicketPriority, TicketStatus, User, UserRole
from services.triage_service import TriageResult
from tasks import ticket_tasks


def test_task_uses_project_database_session_factory():
    assert ticket_tasks.SessionLocal is SessionLocal


@pytest.fixture
def task_database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    next_ids = {Team: 1, TicketAssignment: 1, KnowledgeBaseArticle: 1}

    def assign_sqlite_ids(db_session, flush_context, instances):
        for value in db_session.new:
            if isinstance(value, (Team, TicketAssignment, KnowledgeBaseArticle)) and value.id is None:
                value.id = next_ids[type(value)]
                next_ids[type(value)] += 1

    event.listen(Session, "before_flush", assign_sqlite_ids)
    now = datetime.now(timezone.utc)
    session.add_all(
        [
            User(id=1, name="Employee", email="employee@example.com", role=UserRole.EMPLOYEE),
            Ticket(
                id=1,
                title="VPN outage",
                description="The company VPN is unavailable.",
                creator_id=1,
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.NEW,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    session.commit()
    monkeypatch.setattr(ticket_tasks, "create_task_session", session_factory)
    yield session
    event.remove(Session, "before_flush", assign_sqlite_ids)
    session.close()
    Base.metadata.drop_all(engine)


def fake_triage_result():
    return TriageResult(
        category="Network",
        subcategory=None,
        priority=TicketPriority.HIGH,
        confidence=0.91,
        model_version="test-model",
    )


def test_process_ticket_success(task_database, monkeypatch):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())

    result = ticket_tasks.process_ticket.run(1)
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assignment = task_database.query(TicketAssignment).one()

    assert result == {"status": "processed", "ticket_id": 1}
    assert ticket.ai_predicted_category == "Network"
    assert ticket.ai_predicted_priority == TicketPriority.HIGH
    assert ticket.solution_status == "NO_MATCH"
    assert ticket.suggested_solution is None
    assert ticket.knowledge_article_id is None
    assert ticket.solution_confidence is None
    assert ticket.ai_triaged_at is not None
    assert ticket.assigned_team_id == assignment.team_id
    assert assignment.source == AssignmentSource.AI


def test_process_ticket_missing_ticket(task_database):
    assert ticket_tasks.process_ticket.run(999) == {"status": "missing", "ticket_id": 999}


def test_process_ticket_rolls_back_on_triage_failure(task_database, monkeypatch):
    def fail_triage(self, title, description):
        raise RuntimeError("triage failed")

    monkeypatch.setattr(ticket_tasks.TriageService, "triage", fail_triage)

    with pytest.raises(RuntimeError, match="triage failed"):
        ticket_tasks.process_ticket.run(1)

    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.ai_predicted_category is None
    assert ticket.ai_predicted_priority is None
    assert task_database.query(TicketAssignment).count() == 0


def test_process_ticket_rolls_back_on_routing_failure(task_database, monkeypatch):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())

    def fail_routing(self, db, ticket, triage_result):
        raise RuntimeError("routing failed")

    monkeypatch.setattr(ticket_tasks.RoutingService, "route_and_assign", fail_routing)

    with pytest.raises(RuntimeError, match="routing failed"):
        ticket_tasks.process_ticket.run(1)

    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.ai_predicted_category is None
    assert ticket.assigned_team_id is None
    assert task_database.query(TicketAssignment).count() == 0


def test_process_ticket_is_idempotent(task_database, monkeypatch):
    triage_calls = 0

    def count_triage(self, title, description):
        nonlocal triage_calls
        triage_calls += 1
        return fake_triage_result()

    monkeypatch.setattr(ticket_tasks.TriageService, "triage", count_triage)

    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    assert ticket_tasks.process_ticket.run(1) == {"status": "already_processed", "ticket_id": 1}
    assert triage_calls == 1
    assert task_database.query(TicketAssignment).count() == 1


def test_process_ticket_persists_solution_recommendation(task_database, monkeypatch):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())
    task_database.add(KnowledgeBaseArticle(id=1, title="VPN troubleshooting", summary="VPN connection", category="Network", resolution_steps="Reconnect using the approved VPN client.", keywords="vpn remote tunnel", active=True))
    task_database.commit()

    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.solution_status == "MATCHED"
    assert ticket.knowledge_article_id == 1
    assert "approved VPN" in ticket.suggested_solution
    assert ticket.solution_confidence > 0


def test_process_ticket_continues_when_knowledge_base_fails(task_database, monkeypatch, caplog):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())

    def fail_retrieval(self, db, title, description, category):
        raise RuntimeError("knowledge store unavailable")

    monkeypatch.setattr(ticket_tasks.KnowledgeBaseService, "retrieve", fail_retrieval)

    result = ticket_tasks.process_ticket.run(1)
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assignment = task_database.query(TicketAssignment).one()

    assert result == {"status": "processed", "ticket_id": 1}
    assert ticket.ai_predicted_category == "Network"
    assert ticket.ai_predicted_priority == TicketPriority.HIGH
    assert float(ticket.ai_confidence) == pytest.approx(0.91)
    assert ticket.ai_model_version == "test-model"
    assert ticket.ai_triaged_at is not None
    assert ticket.assigned_team_id == assignment.team_id
    assert assignment.source == AssignmentSource.AI
    assert ticket.solution_status == "NO_MATCH"
    assert ticket.suggested_solution is None
    assert ticket.knowledge_article_id is None
    assert ticket.solution_confidence is None
    assert "ticket_id=1" in caplog.text
    assert "knowledge store unavailable" in caplog.text
