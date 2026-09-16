"""Add structured ticket field override history.

Revision ID: 0002_ticket_field_history
Revises: 0001_initial_schema
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_ticket_field_history"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_field_history",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("changed_by_id", sa.BigInteger(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE", name="fk_field_history_ticket"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="RESTRICT", name="fk_field_history_user"),
        sa.CheckConstraint("field_name IN ('category', 'subcategory', 'priority')", name="chk_field_history_field_name"),
        sa.CheckConstraint("old_value IS DISTINCT FROM new_value", name="chk_field_history_changed"),
    )
    op.create_index("idx_ticket_field_history_ticket", "ticket_field_history", ["ticket_id", "changed_at"])


def downgrade() -> None:
    op.drop_index("idx_ticket_field_history_ticket", table_name="ticket_field_history")
    op.drop_table("ticket_field_history")
