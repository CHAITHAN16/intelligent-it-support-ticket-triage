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


@dataclass(frozen=True)
class SLAClockCalculation:
    target_minutes: int
    deadline: datetime
    completed_at: datetime | None
    state: str
    remaining_seconds: int | None
    overdue_seconds: int | None
    actively_overdue: bool


@dataclass(frozen=True)
class TicketSLACalculation:
    response: SLAClockCalculation
    resolution: SLAClockCalculation
    actively_overdue: bool


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        # SQLite drops tzinfo when round-tripping timezone=True columns.
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _clock_result(
    *,
    target_minutes: int,
    deadline: datetime,
    completed_at: datetime | None,
    now: datetime,
    terminal_without_completion: bool,
    approaching_within_minutes: int,
) -> SLAClockCalculation:
    completion_utc = _aware_utc(completed_at) if completed_at else None
    if terminal_without_completion:
        return SLAClockCalculation(target_minutes, deadline, None, "NOT_APPLICABLE", None, None, False)
    if completion_utc is not None:
        breached = completion_utc > deadline
        return SLAClockCalculation(
            target_minutes, deadline, completion_utc, "BREACHED" if breached else "MET",
            None, max(0, int((completion_utc - deadline).total_seconds())) if breached else None, False,
        )
    if now > deadline:
        return SLAClockCalculation(
            target_minutes, deadline, None, "BREACHED", None,
            int((now - deadline).total_seconds()), True,
        )
    remaining = max(0, int((deadline - now).total_seconds()))
    state = "APPROACHING" if remaining <= approaching_within_minutes * 60 else "ON_TRACK"
    return SLAClockCalculation(target_minutes, deadline, None, state, remaining, None, False)


def calculate_ticket_sla(
    ticket: Ticket,
    target: SLATarget,
    now: datetime | None = None,
    *,
    approaching_within_minutes: int = 60,
) -> SLACalculation:
    """Calculate elapsed-calendar-time deadlines using timezone-aware UTC instants."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    created_utc = _aware_utc(ticket.created_at)
    response_deadline = created_utc + timedelta(minutes=target.response_minutes)
    resolution_deadline = created_utc + timedelta(minutes=target.resolution_minutes)
    terminal = ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    now_utc = current.astimezone(timezone.utc)
    response_time = _aware_utc(ticket.first_response_at) if ticket.first_response_at else now_utc
    resolution_time = _aware_utc(ticket.resolved_at) if ticket.resolved_at else now_utc
    # A response/resolution completed after its deadline remains a recorded breach.
    response_overdue = response_time.astimezone(timezone.utc) > response_deadline
    resolution_overdue = resolution_time.astimezone(timezone.utc) > resolution_deadline
    return SLACalculation(
        response_deadline=response_deadline,
        resolution_deadline=resolution_deadline,
        response_overdue=response_overdue,
        resolution_overdue=resolution_overdue,
        actively_overdue=not terminal and (
            ticket.first_response_at is None and response_overdue
            or ticket.resolved_at is None and resolution_overdue
        ),
    )


def calculate_ticket_sla_clocks(
    ticket: Ticket,
    target: SLATarget,
    now: datetime | None = None,
    *,
    approaching_within_minutes: int = 60,
) -> TicketSLACalculation:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_utc = current.astimezone(timezone.utc)
    created = _aware_utc(ticket.created_at)
    response_deadline = created + timedelta(minutes=target.response_minutes)
    resolution_deadline = created + timedelta(minutes=target.resolution_minutes)
    terminal = ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    response = _clock_result(
        target_minutes=target.response_minutes,
        deadline=response_deadline,
        completed_at=ticket.first_response_at,
        now=now_utc,
        terminal_without_completion=False,
        approaching_within_minutes=approaching_within_minutes,
    )
    resolution = _clock_result(
        target_minutes=target.resolution_minutes,
        deadline=resolution_deadline,
        completed_at=ticket.resolved_at,
        now=now_utc,
        terminal_without_completion=terminal and ticket.resolved_at is None,
        approaching_within_minutes=approaching_within_minutes,
    )
    return TicketSLACalculation(
        response=response,
        resolution=resolution,
        actively_overdue=not terminal and (response.actively_overdue or resolution.actively_overdue),
    )
