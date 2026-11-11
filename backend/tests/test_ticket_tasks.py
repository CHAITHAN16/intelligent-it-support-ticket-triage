import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from celery.exceptions import Retry
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import SessionLocal
from models import AssignmentSource, Base, KnowledgeBaseArticle, Team, Ticket, TicketAssignment, TicketPredictionEvidence, TicketPriority, TicketStatus, User, UserRole
from services.triage_service import CATEGORY_MODEL_VERSION, MODEL_VERSION, PRIORITY_MODEL_VERSION, TriageResult
from tasks import ticket_tasks


def test_task_uses_project_database_session_factory():
    assert ticket_tasks.SessionLocal is SessionLocal
    assert ticket_tasks.process_ticket.max_retries == 3
    assert ticket_tasks.process_ticket.autoretry_for == (
        OperationalError,
        ConnectionError,
        TimeoutError,
    )


@pytest.fixture
def task_database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    next_ids = {Team: 1, TicketAssignment: 1, KnowledgeBaseArticle: 1, TicketPredictionEvidence: 1}

    def assign_sqlite_ids(db_session, flush_context, instances):
        for value in db_session.new:
            if isinstance(value, (Team, TicketAssignment, KnowledgeBaseArticle, TicketPredictionEvidence)) and value.id is None:
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
        classification_confidence=0.84,
        confidence=0.91,
        model_version=MODEL_VERSION,
        category_model_version=CATEGORY_MODEL_VERSION,
        priority_model_version=PRIORITY_MODEL_VERSION,
        category_probabilities={"Network": 0.84, "Other": 0.04, "Security": 0.07, "Software": 0.05},
        priority_probabilities={"LOW": 0.03, "MEDIUM": 0.12, "HIGH": 0.85},
    )


def test_process_ticket_success(task_database, monkeypatch):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())

    result = ticket_tasks.process_ticket.run(1)
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assignment = task_database.query(TicketAssignment).one()
    evidence = task_database.query(TicketPredictionEvidence).one()

    assert result == {"status": "processed", "ticket_id": 1}
    assert ticket.ai_predicted_category == "Network"
    assert ticket.category == "Network"
    assert ticket.ai_predicted_priority == TicketPriority.HIGH
    assert float(ticket.ai_classification_confidence) == pytest.approx(0.84)
    assert ticket.solution_status == "NO_MATCH"
    assert ticket.suggested_solution is None
    assert ticket.knowledge_article_id is None
    assert ticket.solution_confidence is None
    assert ticket.ai_triaged_at is not None
    assert ticket.assigned_team_id == assignment.team_id
    assert assignment.source == AssignmentSource.AI
    assert evidence.ticket_id == 1
    assert evidence.predicted_category == "Network"
    assert evidence.predicted_priority == TicketPriority.HIGH
    assert evidence.category_model_version == CATEGORY_MODEL_VERSION
    assert evidence.priority_model_version == PRIORITY_MODEL_VERSION
    assert evidence.runtime_model_version == MODEL_VERSION
    assert evidence.category_probabilities == {"Network": 0.84, "Other": 0.04, "Security": 0.07, "Software": 0.05}
    assert evidence.priority_probabilities == {"LOW": 0.03, "MEDIUM": 0.12, "HIGH": 0.85}
    assert float(evidence.classification_confidence) == pytest.approx(0.84)
    assert float(evidence.combined_confidence) == pytest.approx(0.91)
    assert evidence.predicted_at == ticket.ai_triaged_at


def test_process_ticket_missing_ticket(task_database):
    assert ticket_tasks.process_ticket.run(999) == {"status": "missing", "ticket_id": 999}


def test_process_ticket_rolls_back_on_triage_failure(task_database, monkeypatch):
    def fail_triage(self, title, description):
        raise OperationalError("triage", {}, RuntimeError("database temporarily unavailable"))

    monkeypatch.setattr(ticket_tasks.TriageService, "triage", fail_triage)
    retry_requests = []

    def request_retry(**kwargs):
        retry_requests.append(kwargs)
        raise Retry(exc=kwargs["exc"])

    monkeypatch.setattr(
        ticket_tasks.process_ticket,
        "retry",
        request_retry,
    )

    with pytest.raises(Retry):
        ticket_tasks.process_ticket.run(1)
    assert len(retry_requests) == 1
    assert isinstance(retry_requests[0]["exc"], OperationalError)

    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.ai_predicted_category is None
    assert ticket.ai_predicted_priority is None
    assert task_database.query(TicketAssignment).count() == 0


def test_process_ticket_rolls_back_on_routing_failure(task_database, monkeypatch):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())

    def fail_routing(self, db, ticket, triage_result):
        raise OperationalError("routing", {}, RuntimeError("database temporarily unavailable"))

    monkeypatch.setattr(ticket_tasks.RoutingService, "route_and_assign", fail_routing)
    retry_requests = []

    def request_retry(**kwargs):
        retry_requests.append(kwargs)
        raise Retry(exc=kwargs["exc"])

    monkeypatch.setattr(
        ticket_tasks.process_ticket,
        "retry",
        request_retry,
    )

    with pytest.raises(Retry):
        ticket_tasks.process_ticket.run(1)
    assert len(retry_requests) == 1
    assert isinstance(retry_requests[0]["exc"], OperationalError)

    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.ai_predicted_category is None
    assert ticket.assigned_team_id is None
    assert task_database.query(TicketAssignment).count() == 0


def test_process_ticket_does_not_retry_permanent_model_errors(task_database, monkeypatch):
    def fail_triage(self, title, description):
        raise ValueError("unsupported model output")

    monkeypatch.setattr(ticket_tasks.TriageService, "triage", fail_triage)

    with pytest.raises(ValueError, match="unsupported model output"):
        ticket_tasks.process_ticket.run(1)


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
    assert task_database.query(TicketPredictionEvidence).count() == 1


def test_process_ticket_appends_new_evidence_without_overwriting_previous(
    task_database, monkeypatch
):
    original = fake_triage_result()
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: original)
    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    first = task_database.query(TicketPredictionEvidence).one()
    first_id = first.id
    first_probabilities = dict(first.category_probabilities)

    ticket = task_database.get(Ticket, 1)
    ticket.solution_status = None
    task_database.commit()
    second = TriageResult(
        category="Security",
        subcategory=None,
        priority=TicketPriority.MEDIUM,
        classification_confidence=0.72,
        confidence=0.68,
        model_version=MODEL_VERSION,
        category_model_version=CATEGORY_MODEL_VERSION,
        priority_model_version=PRIORITY_MODEL_VERSION,
        category_probabilities={"Network": 0.10, "Other": 0.08, "Security": 0.72, "Software": 0.10},
        priority_probabilities={"LOW": 0.10, "MEDIUM": 0.68, "HIGH": 0.22},
    )
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: second)

    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    evidence = task_database.query(TicketPredictionEvidence).order_by(TicketPredictionEvidence.id).all()
    assert len(evidence) == 2
    assert evidence[0].id == first_id
    assert evidence[0].predicted_category == "Network"
    assert evidence[0].category_probabilities == first_probabilities
    assert evidence[1].predicted_category == "Security"
    assert evidence[1].category_probabilities == second.category_probabilities


def test_process_ticket_persists_subcategory(task_database, monkeypatch):
    result = TriageResult(
        category="Network",
        subcategory="VPN",
        priority=TicketPriority.HIGH,
        classification_confidence=0.84,
        confidence=0.91,
        model_version=MODEL_VERSION,
    )
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: result)
    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    assert task_database.get(Ticket, 1).subcategory == "VPN"


def test_process_ticket_repairs_partial_ticket_without_duplicate_assignment(task_database, monkeypatch):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())
    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    ticket.category = None
    ticket.solution_status = None
    task_database.commit()

    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.category == "Network"
    assert ticket.solution_status == "NO_MATCH"
    assert task_database.query(TicketAssignment).count() == 1


def test_process_ticket_repairs_only_missing_confidence(task_database, monkeypatch):
    monkeypatch.setattr(
        ticket_tasks.TriageService,
        "triage",
        lambda self, title, description: fake_triage_result(),
    )
    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    before = {
        "category": ticket.category,
        "subcategory": ticket.subcategory,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_team_id": ticket.assigned_team_id,
        "assigned_agent_id": ticket.assigned_agent_id,
        "predicted_category": ticket.ai_predicted_category,
        "predicted_priority": ticket.ai_predicted_priority,
        "combined_confidence": ticket.ai_confidence,
        "model_version": ticket.ai_model_version,
        "triaged_at": ticket.ai_triaged_at,
        "routing_reason": ticket.routing_reason,
        "solution_status": ticket.solution_status,
        "suggested_solution": ticket.suggested_solution,
        "knowledge_article_id": ticket.knowledge_article_id,
        "solution_confidence": ticket.solution_confidence,
        "updated_at": ticket.updated_at,
    }
    ticket.ai_classification_confidence = None
    task_database.commit()

    def unexpected_full_triage(self, title, description):
        raise AssertionError("confidence-only repair must not rerun triage")

    monkeypatch.setattr(ticket_tasks.TriageService, "triage", unexpected_full_triage)
    monkeypatch.setattr(
        ticket_tasks.TriageService,
        "classification_confidence_for_category",
        lambda self, title, description, expected_category: 0.63,
    )

    assert ticket_tasks.process_ticket.run(1) == {
        "status": "confidence_repaired",
        "ticket_id": 1,
    }
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert float(ticket.ai_classification_confidence) == pytest.approx(0.63)
    assert {
        "category": ticket.category,
        "subcategory": ticket.subcategory,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_team_id": ticket.assigned_team_id,
        "assigned_agent_id": ticket.assigned_agent_id,
        "predicted_category": ticket.ai_predicted_category,
        "predicted_priority": ticket.ai_predicted_priority,
        "combined_confidence": ticket.ai_confidence,
        "model_version": ticket.ai_model_version,
        "triaged_at": ticket.ai_triaged_at,
        "routing_reason": ticket.routing_reason,
        "solution_status": ticket.solution_status,
        "suggested_solution": ticket.suggested_solution,
        "knowledge_article_id": ticket.knowledge_article_id,
        "solution_confidence": ticket.solution_confidence,
        "updated_at": ticket.updated_at,
    } == before
    assert task_database.query(TicketAssignment).count() == 1


def test_process_ticket_does_not_substitute_a_different_model_version(
    task_database, monkeypatch
):
    monkeypatch.setattr(
        ticket_tasks.TriageService,
        "triage",
        lambda self, title, description: fake_triage_result(),
    )
    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    ticket.ai_classification_confidence = None
    ticket.ai_model_version = "unavailable-model"
    task_database.commit()

    monkeypatch.setattr(
        ticket_tasks.TriageService,
        "triage",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not retriage")),
    )
    assert ticket_tasks.process_ticket.run(1) == {
        "status": "confidence_unavailable",
        "ticket_id": 1,
    }
    task_database.expire_all()
    assert task_database.get(Ticket, 1).ai_classification_confidence is None
    assert task_database.query(TicketAssignment).count() == 1


def test_process_ticket_persists_solution_recommendation(task_database, monkeypatch):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())
    task_database.add(KnowledgeBaseArticle(id=1, title="VPN troubleshooting", summary="VPN connection", category="Network", resolution_steps="Reconnect using the approved VPN client.", keywords="vpn remote tunnel", active=True))
    task_database.commit()
    monkeypatch.setattr(
        ticket_tasks.KnowledgeBaseService,
        "retrieve",
        lambda self, db, title, description, category: type("Solution", (), {
            "status": "MATCHED",
            "suggested_solution": "Reconnect using the approved VPN client.",
            "article_id": 1,
            "confidence": 0.82,
        })(),
    )

    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.solution_status == "MATCHED"
    assert ticket.knowledge_article_id == 1
    assert "approved VPN" in ticket.suggested_solution
    assert ticket.solution_confidence > 0


@pytest.mark.parametrize(("confidence", "expected_status", "expected_article"), [
    (0.82, "MATCHED", 1),
    (0.55, "MATCHED", 1),
    (0.25, "NO_MATCH", None),
])
def test_process_ticket_persists_confidence_aware_recommendation(
    task_database, monkeypatch, confidence, expected_status, expected_article
):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())
    monkeypatch.setattr(
        ticket_tasks.KnowledgeBaseService,
        "retrieve",
        lambda self, db, title, description, category: type("Solution", (), {
            "status": expected_status,
            "suggested_solution": "Try reconnecting." if expected_status == "MATCHED" else None,
            "article_id": expected_article,
            "confidence": confidence,
        })(),
    )

    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.solution_status == expected_status
    assert ticket.knowledge_article_id == expected_article
    assert float(ticket.solution_confidence) == pytest.approx(confidence)
    assert ticket.suggested_solution == ("Try reconnecting." if expected_status == "MATCHED" else None)


def test_process_ticket_persists_no_match(task_database, monkeypatch):
    monkeypatch.setattr(ticket_tasks.TriageService, "triage", lambda self, title, description: fake_triage_result())
    assert ticket_tasks.process_ticket.run(1)["status"] == "processed"
    task_database.expire_all()
    ticket = task_database.get(Ticket, 1)
    assert ticket.solution_status == "NO_MATCH"
    assert ticket.suggested_solution is None
    assert ticket.knowledge_article_id is None
    assert ticket.solution_confidence is None


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
    assert ticket.ai_model_version == MODEL_VERSION
    assert ticket.ai_triaged_at is not None
    assert ticket.assigned_team_id == assignment.team_id
    assert assignment.source == AssignmentSource.AI
    assert ticket.solution_status == "NO_MATCH"
    assert ticket.suggested_solution is None
    assert ticket.knowledge_article_id is None
    assert ticket.solution_confidence is None
    assert "ticket_id=1" in caplog.text
    assert "knowledge store unavailable" in caplog.text
