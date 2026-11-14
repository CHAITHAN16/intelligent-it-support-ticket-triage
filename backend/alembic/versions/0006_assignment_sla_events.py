"""Add agent assignment audit details and SLA configuration/events.

Revision ID: 0006_assignment_sla_events
Revises: 0005_ai_prediction_evidence_reviews
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_assignment_sla_events"
down_revision: Union[str, None] = "0005_ai_prediction_evidence_reviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    priority = postgresql.ENUM(name="ticket_priority", create_type=False)
    op.add_column("tickets", sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ticket_assignments", sa.Column("previous_agent_id", sa.BigInteger(), nullable=True))
    op.add_column("ticket_assignments", sa.Column("reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_assignment_previous_agent", "ticket_assignments", "users",
        ["previous_agent_id"], ["id"], ondelete="RESTRICT",
    )

    op.create_table(
        "sla_targets",
        sa.Column("priority", priority, primary_key=True, nullable=False),
        sa.Column("response_minutes", sa.Integer(), nullable=False),
        sa.Column("resolution_minutes", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("response_minutes > 0", name="chk_sla_response_minutes_positive"),
        sa.CheckConstraint("resolution_minutes > 0", name="chk_sla_resolution_minutes_positive"),
    )
    op.create_check_constraint(
        "chk_sla_resolution_after_response", "sla_targets",
        "resolution_minutes >= response_minutes",
    )
    op.bulk_insert(
        sa.table(
            "sla_targets",
            sa.column("priority", priority),
            sa.column("response_minutes", sa.Integer()),
            sa.column("resolution_minutes", sa.Integer()),
        ),
        [
            {"priority": "LOW", "response_minutes": 1440, "resolution_minutes": 7200},
            {"priority": "MEDIUM", "response_minutes": 480, "resolution_minutes": 4320},
            {"priority": "HIGH", "response_minutes": 240, "resolution_minutes": 1440},
            {"priority": "URGENT", "response_minutes": 60, "resolution_minutes": 240},
        ],
    )

    op.create_table(
        "ticket_first_responses",
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("comment_id", sa.BigInteger(), nullable=False),
        sa.Column("agent_id", sa.BigInteger(), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("ticket_id", name="pk_ticket_first_responses"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agent_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("comment_id", name="uq_ticket_first_responses_comment"),
    )
    op.create_index(
        "idx_ticket_first_responses_responded_at",
        "ticket_first_responses",
        ["responded_at"],
    )


def downgrade() -> None:
    raise RuntimeError("This assignment and SLA migration is forward-only")
