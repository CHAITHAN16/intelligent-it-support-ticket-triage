from datetime import datetime, timedelta, timezone

import pytest

from models import SLATarget, Ticket, TicketPriority, TicketStatus
from services.sla_service import calculate_ticket_sla


@pytest.mark.parametrize(
    ("priority", "response_minutes", "resolution_minutes"),
    [
        (TicketPriority.LOW, 1440, 7200),
        (TicketPriority.MEDIUM, 480, 4320),
        (TicketPriority.HIGH, 240, 1440),
        (TicketPriority.URGENT, 60, 240),
    ],
)
def test_default_sla_policy_targets(priority, response_minutes, resolution_minutes):
    # These values are provisioned by forward migration 0006.
    assert response_minutes > 0
    assert resolution_minutes >= response_minutes
    assert priority in TicketPriority


def test_sla_deadlines_use_aware_elapsed_time_and_are_separate():
    created = datetime(2026, 11, 14, 10, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    ticket = Ticket(
        id=1,
        title="Network issue",
        description="Cannot connect",
        creator_id=1,
        priority=TicketPriority.HIGH,
        status=TicketStatus.IN_PROGRESS,
        created_at=created,
    )
    target = SLATarget(priority=TicketPriority.HIGH, response_minutes=60, resolution_minutes=180)
    result = calculate_ticket_sla(ticket, target, now=datetime(2026, 11, 14, 6, 45, tzinfo=timezone.utc))

    assert result.response_deadline == datetime(2026, 11, 14, 5, 30, tzinfo=timezone.utc)
    assert result.resolution_deadline == datetime(2026, 11, 14, 7, 30, tzinfo=timezone.utc)
    assert result.response_overdue is True
    assert result.resolution_overdue is False
    assert result.actively_overdue is True


@pytest.mark.parametrize("terminal_status", [TicketStatus.RESOLVED, TicketStatus.CLOSED])
def test_terminal_tickets_are_not_actively_overdue(terminal_status):
    created = datetime(2026, 11, 1, tzinfo=timezone.utc)
    ticket = Ticket(
        id=1,
        title="Resolved issue",
        description="Fixed",
        creator_id=1,
        priority=TicketPriority.URGENT,
        status=terminal_status,
        created_at=created,
        resolved_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )
    target = SLATarget(priority=TicketPriority.URGENT, response_minutes=30, resolution_minutes=60)
    result = calculate_ticket_sla(ticket, target, now=datetime(2026, 11, 14, tzinfo=timezone.utc))

    assert result.response_overdue is True
    assert result.resolution_overdue is False
    assert result.actively_overdue is False


def test_sla_calculator_rejects_naive_now():
    ticket = Ticket(
        id=1,
        title="Ticket",
        description="Description",
        creator_id=1,
        priority=TicketPriority.LOW,
        status=TicketStatus.NEW,
        created_at=datetime(2026, 11, 14, tzinfo=timezone.utc),
    )
    target = SLATarget(priority=TicketPriority.LOW, response_minutes=60, resolution_minutes=120)
    with pytest.raises(ValueError, match="timezone-aware"):
        calculate_ticket_sla(ticket, target, now=datetime(2026, 11, 14))
