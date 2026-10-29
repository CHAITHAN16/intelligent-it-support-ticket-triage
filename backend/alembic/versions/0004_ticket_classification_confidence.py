"""Persist category-model confidence separately from combined triage score."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_ticket_classification_confidence"
down_revision: Union[str, None] = "0003_ai_resolution_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("ai_classification_confidence", sa.Numeric(5, 4), nullable=True))
    op.create_check_constraint(
        "chk_ai_classification_confidence",
        "tickets",
        "ai_classification_confidence IS NULL OR ai_classification_confidence BETWEEN 0 AND 1",
    )


def downgrade() -> None:
    op.drop_constraint("chk_ai_classification_confidence", "tickets", type_="check")
    op.drop_column("tickets", "ai_classification_confidence")