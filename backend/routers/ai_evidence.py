from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import require_agent
from database import get_db
from models import (
    Ticket,
    TicketFieldHistory,
    TicketPredictionEvidence,
    TicketPredictionReview,
    User,
)
from routers.tickets import _require_ticket_access
from schemas.ai_evidence import (
    TicketPredictionEvidenceResponse,
    TicketPredictionReviewCreate,
    TicketPredictionReviewResponse,
)


router = APIRouter(prefix="/api/tickets", tags=["ai-prediction-evidence"])


def _authorized_ticket(ticket_id: int, current_user: User, db: Session) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    _require_ticket_access(ticket, current_user, db, allow_employee=False)
    return ticket


@router.get(
    "/{ticket_id}/prediction-evidence",
    response_model=list[TicketPredictionEvidenceResponse],
    summary="List ticket AI prediction evidence",
)
def list_prediction_evidence(
    ticket_id: int,
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db),
) -> list[TicketPredictionEvidence]:
    _authorized_ticket(ticket_id, current_user, db)
    return list(
        db.scalars(
            select(TicketPredictionEvidence)
            .where(TicketPredictionEvidence.ticket_id == ticket_id)
            .order_by(TicketPredictionEvidence.predicted_at.asc(), TicketPredictionEvidence.id.asc())
        ).all()
    )


@router.get(
    "/{ticket_id}/prediction-reviews",
    response_model=list[TicketPredictionReviewResponse],
    summary="List human reviews of ticket AI predictions",
)
def list_prediction_reviews(
    ticket_id: int,
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db),
) -> list[TicketPredictionReview]:
    _authorized_ticket(ticket_id, current_user, db)
    return list(
        db.scalars(
            select(TicketPredictionReview)
            .where(TicketPredictionReview.ticket_id == ticket_id)
            .order_by(TicketPredictionReview.reviewed_at.asc(), TicketPredictionReview.id.asc())
        ).all()
    )


@router.post(
    "/{ticket_id}/prediction-reviews",
    response_model=list[TicketPredictionReviewResponse],
    status_code=201,
    summary="Accept or correct AI ticket predictions",
)
def review_ticket_prediction(
    ticket_id: int,
    payload: TicketPredictionReviewCreate,
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db),
) -> list[TicketPredictionReview]:
    ticket = _authorized_ticket(ticket_id, current_user, db)
    evidence = db.scalar(
        select(TicketPredictionEvidence).where(
            TicketPredictionEvidence.id == payload.prediction_evidence_id,
            TicketPredictionEvidence.ticket_id == ticket_id,
        )
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Prediction evidence was not found for this ticket")

    reviewed_at = datetime.now(timezone.utc)
    reviews: list[TicketPredictionReview] = []
    fields = (
        ("category", payload.category, evidence.predicted_category),
        ("priority", payload.priority, evidence.predicted_priority.value if evidence.predicted_priority else None),
    )

    try:
        for field_name, confirmed, predicted in fields:
            if confirmed is None:
                continue
            confirmed_value = confirmed.value if hasattr(confirmed, "value") else confirmed
            outcome = "ACCEPTED" if confirmed_value == predicted else "OVERRIDDEN"
            review = TicketPredictionReview(
                ticket_id=ticket_id,
                prediction_evidence_id=evidence.id,
                reviewer_id=current_user.id,
                field_name=field_name,
                predicted_value=predicted,
                confirmed_value=confirmed_value,
                outcome=outcome,
                reviewed_at=reviewed_at,
                reason=payload.reason,
            )
            db.add(review)
            reviews.append(review)

            if outcome == "OVERRIDDEN":
                old_value = getattr(ticket, field_name)
                if old_value != confirmed:
                    setattr(ticket, field_name, confirmed)
                    db.add(
                        TicketFieldHistory(
                            ticket_id=ticket_id,
                            field_name=field_name,
                            old_value=old_value.value if hasattr(old_value, "value") else old_value,
                            new_value=confirmed_value,
                            changed_by_id=current_user.id,
                            changed_at=reviewed_at,
                            note=payload.reason,
                        )
                    )
                    ticket.updated_at = reviewed_at

        db.commit()
        for review in reviews:
            db.refresh(review)
        return reviews
    except Exception:
        db.rollback()
        raise
