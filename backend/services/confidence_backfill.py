from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models import Ticket
from services.triage_service import (
    MODEL_VERSION,
    ConfidencePredictionMismatchError,
    TriageService,
)


@dataclass
class ConfidenceBackfillSummary:
    scanned: int = 0
    ready: int = 0
    updated: int = 0
    skipped: dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1


def backfill_missing_classification_confidence(
    db: Session,
    *,
    apply: bool = False,
    triage_service: TriageService | None = None,
) -> ConfidenceBackfillSummary:
    """Recalculate only confidence for records verifiably from the configured model."""
    tickets = db.scalars(
        select(Ticket)
        .where(Ticket.ai_classification_confidence.is_(None))
        .order_by(Ticket.id)
    ).all()
    summary = ConfidenceBackfillSummary(scanned=len(tickets))

    try:
        for ticket in tickets:
            if ticket.ai_triaged_at is None:
                summary.skip("not_triaged")
                continue
            if ticket.ai_model_version != MODEL_VERSION:
                summary.skip("unsupported_or_missing_model_version")
                continue
            if not ticket.ai_predicted_category:
                summary.skip("missing_stored_category_prediction")
                continue

            if triage_service is None:
                triage_service = TriageService()
            try:
                confidence = triage_service.classification_confidence_for_category(
                    ticket.title,
                    ticket.description,
                    ticket.ai_predicted_category,
                )
            except ConfidencePredictionMismatchError:
                summary.skip("current_model_prediction_mismatch")
                continue

            summary.ready += 1
            if not apply:
                continue

            result = db.execute(
                update(Ticket)
                .where(
                    Ticket.id == ticket.id,
                    Ticket.ai_classification_confidence.is_(None),
                    Ticket.ai_triaged_at.is_not(None),
                    Ticket.ai_model_version == MODEL_VERSION,
                    Ticket.ai_predicted_category == ticket.ai_predicted_category,
                    Ticket.title == ticket.title,
                    Ticket.description == ticket.description,
                    Ticket.ai_triaged_at == ticket.ai_triaged_at,
                )
                .values(ai_classification_confidence=confidence)
            )
            if result.rowcount == 1:
                summary.updated += 1
            else:
                summary.skip("changed_concurrently")

        if apply:
            db.commit()
        return summary
    except Exception:
        db.rollback()
        raise
