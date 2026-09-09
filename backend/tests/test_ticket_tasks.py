import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from models import AssignmentSource, Base, Team, Ticket, TicketAssignment, TicketPriority, TicketStatus, User, UserRole
from services.triage_service import TriageResult
from tasks import ticket_tasks


@pytest.fixture
def task_database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    next_ids = {Team: 1, TicketAssignment: 1}

    def assign_sqlite_ids(db_session, flush_context, instances):
        for value in db_session.new:
            if isinstance(value, (Team, TicketAssignment)) and value.id is None:
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
    monkeypatch.setattr(ticket_tasks, "SessionLocal", session_factory)
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
