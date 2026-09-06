from datetime import datetime, timezone
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest

from models import Team, Ticket, TicketAssignment, TicketPriority, TicketStatus
from routers.tickets import create_ticket
from schemas.tickets import TicketCreate


class _Savepoint:
    def __init__(self, db):
        self.db = db

    def commit(self):
        pass

    def rollback(self):
        self.db.savepoint_rollbacks += 1


class InMemorySession:
    """Small session double for transaction and assignment behavior tests."""

    def __init__(self, fail_on_assignment=False):
        self.teams = []
        self.assignments = []
        self.added = []
        self.fail_on_assignment = fail_on_assignment
        self.rollback_called = False
        self.commit_called = False
        self.savepoint_rollbacks = 0
        self.next_team_id = 1

    def scalar(self, statement):
        # The production query is constrained by the teams.name unique key.
        # This double has one pre-seeded team at most, which is sufficient to
        # verify lookup versus creation without implementing SQLAlchemy parsing.
        return self.teams[0] if self.teams else None

    def begin_nested(self):
        return _Savepoint(self)

    def add(self, value):
        if isinstance(value, TicketAssignment) and self.fail_on_assignment:
            raise RuntimeError("assignment insert failed")
        self.added.append(value)
        if isinstance(value, Team) and value not in self.teams:
            value.id = self.next_team_id
            self.next_team_id += 1
            self.teams.append(value)
        if isinstance(value, TicketAssignment):
            self.assignments.append(value)

    def flush(self):
        for value in self.added:
            if isinstance(value, Ticket) and value.id is None:
                value.id = 1
                now = datetime.now(timezone.utc)
                value.created_at = now
                value.updated_at = now

    def commit(self):
        self.commit_called = True

    def refresh(self, value):
        pass

    def rollback(self):
        self.rollback_called = True


@pytest.mark.parametrize(
    ("title", "description", "expected_category", "expected_priority", "expected_team"),
    [
        (
            "VPN connection keeps dropping",
            "I cannot maintain a connection to the company VPN and the network keeps disconnecting.",
            "Network",
            "MEDIUM",
            "Network Infrastructure",
        ),
        (
            "Critical security breach detected",
            "We detected unauthorized access and suspicious malware activity on a company system.",
            "Security",
            "HIGH",
            "Security Operations",
        ),
        (
            "Application keeps crashing",
            "The internal application crashes whenever I try to open the reporting module.",
            "Software",
            "HIGH",
            "Software Support",
        ),
        (
            "Marketing campaign question",
            "I need information about our upcoming marketing campaign.",
            "Other",
            "MEDIUM",
            "General IT Support",
        ),
    ],
)
def test_ticket_creation_persists_ai_team_assignment(
    title,
    description,
    expected_category,
    expected_priority,
    expected_team,
):
    db = InMemorySession()
    ticket = create_ticket(
        TicketCreate(title=title, description=description, creator_id=1),
        db,
    )

    assert ticket.ai_predicted_category == expected_category
    assert ticket.ai_predicted_priority.value == expected_priority
    assert ticket.assigned_team_id == db.teams[0].id
    assert ticket.assigned_agent_id is None
    assert len(db.assignments) == 1
    assert db.assignments[0].ticket_id == ticket.id
    assert db.assignments[0].team_id == ticket.assigned_team_id
    assert db.assignments[0].agent_id is None
    assert db.commit_called
    assert not db.rollback_called
    assert db.teams[0].name == expected_team


def test_existing_team_is_reused_without_duplicate():
    db = InMemorySession()
    existing_team = Team(name="Network Infrastructure")
    existing_team.id = 42
    db.teams.append(existing_team)

    ticket = create_ticket(
        TicketCreate(
            title="VPN connection keeps dropping",
            description="The company VPN disconnects repeatedly.",
            creator_id=1,
        ),
        db,
    )

    assert ticket.assigned_team_id == 42
    assert [team.name for team in db.teams] == ["Network Infrastructure"]
    assert len(db.assignments) == 1


def test_assignment_failure_rolls_back_ticket_transaction():
    db = InMemorySession(fail_on_assignment=True)

    with pytest.raises(RuntimeError, match="assignment insert failed"):
        create_ticket(
            TicketCreate(
                title="VPN connection keeps dropping",
                description="The company VPN disconnects repeatedly.",
                creator_id=1,
            ),
            db,
        )

    assert db.rollback_called
    assert not db.commit_called
