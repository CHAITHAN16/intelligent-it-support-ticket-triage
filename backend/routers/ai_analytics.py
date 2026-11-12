from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from auth import require_agent
from database import get_db
from models import Team, TeamMember, Ticket, TicketAssignment, TicketPredictionEvidence, TicketPredictionReview, User, UserRole

router = APIRouter(prefix="/api/analytics", tags=["ai-analytics"])


@router.get("/ai", summary="Aggregate AI prediction review analytics")
def ai_analytics(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    model_version: str | None = Query(default=None, max_length=150),
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="The start date must be on or before the end date")
    start = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    visible_ticket = select(Ticket.id)
    if current_user.role != UserRole.ADMIN:
        visible_ticket = visible_ticket.where(or_(
            Ticket.assigned_agent_id == current_user.id,
            Ticket.assigned_team_id.in_(select(TeamMember.team_id).where(TeamMember.user_id == current_user.id)),
        ))
    latest_ids = (
        select(
            TicketPredictionEvidence.id.label("evidence_id"),
            func.row_number().over(
                partition_by=TicketPredictionEvidence.ticket_id,
                order_by=(TicketPredictionEvidence.predicted_at.desc(), TicketPredictionEvidence.id.desc()),
            ).label("row_num"),
        )
        .where(
            TicketPredictionEvidence.predicted_at >= start,
            TicketPredictionEvidence.predicted_at < end,
            TicketPredictionEvidence.ticket_id.in_(visible_ticket),
        )
        .subquery()
    )
    cohort = (
        select(TicketPredictionEvidence.id, TicketPredictionEvidence.ticket_id,
               TicketPredictionEvidence.category_model_version, TicketPredictionEvidence.priority_model_version,
               TicketPredictionEvidence.predicted_at, TicketPredictionEvidence.predicted_category,
               TicketPredictionEvidence.predicted_priority)
        .join(latest_ids, latest_ids.c.evidence_id == TicketPredictionEvidence.id)
        .where(latest_ids.c.row_num == 1)
    )
    if model_version:
        cohort = cohort.where(or_(
            TicketPredictionEvidence.category_model_version == model_version,
            TicketPredictionEvidence.priority_model_version == model_version,
        ))
    cohort = cohort.cte("selected_prediction_cohort")

    totals_row = db.execute(select(
        func.count(cohort.c.id),
        func.count(func.distinct(case((TicketPredictionReview.id.is_not(None), cohort.c.ticket_id)))),
        func.count(case((TicketPredictionReview.field_name == "category", 1))),
        func.count(case((TicketPredictionReview.field_name == "priority", 1))),
    ).select_from(cohort.outerjoin(TicketPredictionReview, TicketPredictionReview.prediction_evidence_id == cohort.c.id))).one()

    def field_counts(field: str):
        return db.execute(select(
            func.count(TicketPredictionReview.id),
            func.coalesce(func.sum(case((TicketPredictionReview.outcome == "ACCEPTED", 1), else_=0)), 0),
            func.coalesce(func.sum(case((TicketPredictionReview.outcome == "OVERRIDDEN", 1), else_=0)), 0),
        ).select_from(cohort.join(TicketPredictionReview, TicketPredictionReview.prediction_evidence_id == cohort.c.id))
          .where(TicketPredictionReview.field_name == field)).one()

    def field_summary(field: str):
        total, accepted, overridden = field_counts(field)
        reviewed = int(total)
        return {"reviewed": reviewed, "accepted": int(accepted), "overridden": int(overridden),
                "acceptance_rate": int(accepted) / reviewed if reviewed else None,
                "override_rate": int(overridden) / reviewed if reviewed else None}

    daily = db.execute(select(
        func.date(TicketPredictionReview.reviewed_at).label("day"),
        func.count(TicketPredictionReview.id).label("reviews"),
        func.count(func.distinct(TicketPredictionReview.ticket_id)).label("tickets"),
    ).select_from(cohort.join(TicketPredictionReview, TicketPredictionReview.prediction_evidence_id == cohort.c.id))
      .where(TicketPredictionReview.reviewed_at >= start, TicketPredictionReview.reviewed_at < end)
      .group_by(func.date(TicketPredictionReview.reviewed_at)).order_by(func.date(TicketPredictionReview.reviewed_at))).all()

    outcome_breakdown = db.execute(select(
        TicketPredictionReview.field_name,
        TicketPredictionReview.predicted_value,
        TicketPredictionReview.outcome,
        func.count(TicketPredictionReview.id),
    ).select_from(cohort.join(TicketPredictionReview, TicketPredictionReview.prediction_evidence_id == cohort.c.id))
      .where(TicketPredictionReview.field_name.in_(["category", "priority"]))
      .group_by(TicketPredictionReview.field_name, TicketPredictionReview.predicted_value, TicketPredictionReview.outcome)
      .order_by(TicketPredictionReview.field_name, TicketPredictionReview.predicted_value, TicketPredictionReview.outcome)).all()

    category_versions = db.execute(select(
        cohort.c.category_model_version,
        func.count(func.distinct(case((TicketPredictionReview.field_name == "category", TicketPredictionReview.ticket_id)))).label("reviewed_tickets"),
        func.count(TicketPredictionReview.id).filter(TicketPredictionReview.field_name == "category").label("reviews"),
        func.coalesce(func.sum(case((and_(TicketPredictionReview.field_name == "category", TicketPredictionReview.outcome == "ACCEPTED"), 1), else_=0)), 0).label("category_accepted"),
        func.coalesce(func.sum(case((and_(TicketPredictionReview.field_name == "category", TicketPredictionReview.outcome == "OVERRIDDEN"), 1), else_=0)), 0).label("category_overridden"),
    ).select_from(cohort.outerjoin(TicketPredictionReview, TicketPredictionReview.prediction_evidence_id == cohort.c.id))
      .group_by(cohort.c.category_model_version).order_by(cohort.c.category_model_version)).all()
    priority_versions = db.execute(select(
        cohort.c.priority_model_version,
        func.count(func.distinct(case((TicketPredictionReview.field_name == "priority", TicketPredictionReview.ticket_id)))).label("reviewed_tickets"),
        func.count(TicketPredictionReview.id).filter(TicketPredictionReview.field_name == "priority").label("reviews"),
        func.coalesce(func.sum(case((and_(TicketPredictionReview.field_name == "priority", TicketPredictionReview.outcome == "ACCEPTED"), 1), else_=0)), 0).label("accepted"),
        func.coalesce(func.sum(case((and_(TicketPredictionReview.field_name == "priority", TicketPredictionReview.outcome == "OVERRIDDEN"), 1), else_=0)), 0).label("overridden"),
    ).select_from(cohort.outerjoin(TicketPredictionReview, TicketPredictionReview.prediction_evidence_id == cohort.c.id))
      .group_by(cohort.c.priority_model_version).order_by(cohort.c.priority_model_version)).all()

    ai_route_rank = select(
        TicketAssignment.ticket_id.label("ticket_id"),
        TicketAssignment.team_id.label("team_id"),
        func.row_number().over(
            partition_by=TicketAssignment.ticket_id,
            order_by=(TicketAssignment.assigned_at.desc(), TicketAssignment.id.desc()),
        ).label("row_num"),
    ).where(
        TicketAssignment.source == "AI", TicketAssignment.assigned_at >= start,
        TicketAssignment.assigned_at < end, TicketAssignment.ticket_id.in_(visible_ticket),
    ).subquery()
    # Resolve the latest AI route per ticket in one aggregate query; no ticket text is selected.
    route_rows = db.execute(select(Team.name, func.count(func.distinct(ai_route_rank.c.ticket_id)))
        .select_from(ai_route_rank).outerjoin(Team, Team.id == ai_route_rank.c.team_id)
        .where(ai_route_rank.c.row_num == 1)
        .group_by(Team.name).order_by(Team.name)).all()

    total_tickets = int(totals_row[0])
    reviewed_tickets = int(totals_row[1])
    cat = field_summary("category")
    pri = field_summary("priority")
    return {
        "from": from_date.isoformat(), "to": to_date.isoformat(), "model_version_filter": model_version,
        "total_prediction_tickets": total_tickets,
        "total_prediction_snapshots": total_tickets,
        "reviewed_prediction_tickets": reviewed_tickets,
        "unreviewed_prediction_tickets": max(0, total_tickets - reviewed_tickets),
        "review_coverage": reviewed_tickets / total_tickets if total_tickets else None,
        "category": cat, "priority": pri,
        "review_activity": [{"date": str(row.day), "reviews": int(row.reviews), "tickets": int(row.tickets)} for row in daily],
        "category_review_breakdown": [{"prediction": row.predicted_value, "outcome": row.outcome, "reviews": int(row[3])} for row in outcome_breakdown if row.field_name == "category"],
        "priority_review_breakdown": [{"prediction": row.predicted_value, "outcome": row.outcome, "reviews": int(row[3])} for row in outcome_breakdown if row.field_name == "priority"],
        "category_model_versions": [{"model_version": row.category_model_version, "reviewed_tickets": int(row.reviewed_tickets), "reviews": int(row.reviews), "accepted": int(row.category_accepted), "overridden": int(row.category_overridden)} for row in category_versions],
        "priority_model_versions": [{"model_version": row.priority_model_version, "reviewed_tickets": int(row.reviewed_tickets), "reviews": int(row.reviews), "accepted": int(row.accepted), "overridden": int(row.overridden)} for row in priority_versions],
        "ai_routing_distribution": [{"team": row.name or "Unassigned", "tickets": int(row[1])} for row in route_rows],
        "limitations": "Rates describe recorded agent review decisions, not model accuracy. The cohort uses at most one latest in-range prediction per ticket. Model groups are observational and may differ in ticket mix.",
    }
