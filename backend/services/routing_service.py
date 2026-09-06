from __future__ import annotations

from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import AssignmentSource, Team, Ticket, TicketAssignment
from services.triage_service import TriageResult


GENERAL_IT_SUPPORT = "General IT Support"

_CATEGORY_TO_TEAM = MappingProxyType(
    {
        "Network": "Network Infrastructure",
        "Security": "Security Operations",
        "Software": "Software Support",
        "Other": GENERAL_IT_SUPPORT,
    }
)


class RoutingService:
    """Routes tickets using only the category produced by AI triage."""

    @staticmethod
    def route_category(category: str | None) -> str:
        """Return the simulated support team for a predicted category."""
        return _CATEGORY_TO_TEAM.get(category, GENERAL_IT_SUPPORT)

    @staticmethod
    def get_or_create_team(db: Session, team_name: str) -> Team:
        """Find a team by its unique name or create it safely."""
        team = db.scalar(select(Team).where(Team.name == team_name))
        if team is not None:
            return team

        new_team = Team(name=team_name)
        savepoint = db.begin_nested()
        try:
            db.add(new_team)
            db.flush()
            savepoint.commit()
            return new_team
        except IntegrityError:
            savepoint.rollback()
            existing_team = db.scalar(select(Team).where(Team.name == team_name))
            if existing_team is None:
                raise
            return existing_team

    def route_and_assign(
        self,
        db: Session,
        ticket: Ticket,
        triage_result: TriageResult,
    ) -> TicketAssignment:
        """Resolve a routed team and create its pending AI assignment.

        The caller owns the surrounding transaction and must commit or roll it
        back after this method returns or raises.
        """
        team_name = self.route_category(triage_result.category)
        team = self.get_or_create_team(db, team_name)

        assignment = TicketAssignment(
            ticket_id=ticket.id,
            team_id=team.id,
            agent_id=None,
            source=AssignmentSource.AI,
            assigned_by_id=None,
            routing_reason=f"AI category '{triage_result.category}' routed to {team_name}",
            model_version=triage_result.model_version,
            ai_confidence=triage_result.confidence,
        )
        db.add(assignment)
        ticket.assigned_team_id = team.id
        ticket.routing_reason = assignment.routing_reason
        db.flush()
        return assignment
