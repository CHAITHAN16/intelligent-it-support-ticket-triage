"""Add append-only ticket prediction evidence and human reviews.

Revision ID: 0005_ai_prediction_evidence_reviews
Revises: 0004_ticket_classification_confidence
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_ai_prediction_evidence_reviews"
down_revision: Union[str, None] = "0004_ticket_classification_confidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ticket_priority = postgresql.ENUM(name="ticket_priority", create_type=False)

    op.create_table(
        "ticket_prediction_evidence",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("predicted_category", sa.String(length=100), nullable=False),
        sa.Column("predicted_priority", ticket_priority, nullable=False),
        sa.Column("category_model_version", sa.String(length=100), nullable=False),
        sa.Column("priority_model_version", sa.String(length=100), nullable=False),
        sa.Column("runtime_model_version", sa.String(length=150), nullable=False),
        sa.Column("category_probabilities", sa.JSON(), nullable=False),
        sa.Column("priority_probabilities", sa.JSON(), nullable=False),
        sa.Column("classification_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("combined_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "classification_confidence BETWEEN 0 AND 1",
            name="chk_evidence_classification_confidence",
        ),
        sa.CheckConstraint(
            "combined_confidence BETWEEN 0 AND 1",
            name="chk_evidence_combined_confidence",
        ),
        sa.UniqueConstraint("id", "ticket_id", name="uq_ticket_prediction_evidence_id_ticket"),
    )
    op.create_index(
        "idx_ticket_prediction_evidence_ticket",
        "ticket_prediction_evidence",
        ["ticket_id", "predicted_at", "id"],
    )

    op.create_table(
        "ticket_prediction_reviews",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("prediction_evidence_id", sa.BigInteger(), nullable=False),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=False),
        sa.Column("field_name", sa.String(length=20), nullable=False),
        sa.Column("predicted_value", sa.String(length=100), nullable=False),
        sa.Column("confirmed_value", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["prediction_evidence_id", "ticket_id"],
            ["ticket_prediction_evidence.id", "ticket_prediction_evidence.ticket_id"],
            name="fk_prediction_review_evidence_ticket",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "field_name IN ('category', 'priority')",
            name="chk_prediction_review_field",
        ),
        sa.CheckConstraint(
            "outcome IN ('ACCEPTED', 'OVERRIDDEN')",
            name="chk_prediction_review_outcome",
        ),
        sa.CheckConstraint(
            "(outcome = 'ACCEPTED' AND predicted_value = confirmed_value) OR "
            "(outcome = 'OVERRIDDEN' AND predicted_value <> confirmed_value)",
            name="chk_prediction_review_outcome_value",
        ),
    )
    op.create_index(
        "idx_ticket_prediction_reviews_ticket",
        "ticket_prediction_reviews",
        ["ticket_id", "reviewed_at", "id"],
    )
    op.create_index(
        "idx_ticket_prediction_reviews_evidence",
        "ticket_prediction_reviews",
        ["prediction_evidence_id"],
    )


def downgrade() -> None:
    raise RuntimeError("This audit-evidence migration is forward-only")
