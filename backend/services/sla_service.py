from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from models import SLATarget, Ticket, TicketStatus


@dataclass(frozen=True)
class SLACalculation:
    response_deadline: datetime
    resolution_deadline: datetime
    response_overdue: bool
    resolution_overdue: bool
    actively_overdue: bool


def calculate_ticket_sla(ticket: Ticket, target: SLATarget, now: datetime | None = None) -> SLACalculation:
    """Calculate elapsed-calendar-time deadlines using timezone-aware UTC instants."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    created = ticket.created_at
    # SQLite drops tzinfo when round-tripping DateTime(timezone=True); treat those
    # test/legacy-naive values as UTC. PostgreSQL persists these columns as timestamptz.
    if created.tzinfo is None or created.utcoffset() is None:
        created = created.replace(tzinfo=timezone.utc)
    created_utc = created.astimezone(timezone.utc)
    response_deadline = created_utc + timedelta(minutes=target.response_minutes)
    resolution_deadline = created_utc + timedelta(minutes=target.resolution_minutes)
    terminal = ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    response_overdue = ticket.first_response_at is None and current.astimezone(timezone.utc) > response_deadline
    resolution_overdue = ticket.resolved_at is None and current.astimezone(timezone.utc) > resolution_deadline
    return SLACalculation(
        response_deadline=response_deadline,
        resolution_deadline=resolution_deadline,
        response_overdue=response_overdue,
        resolution_overdue=resolution_overdue,
        actively_overdue=not terminal and (response_overdue or resolution_overdue),
    )
