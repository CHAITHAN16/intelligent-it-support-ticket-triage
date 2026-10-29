"""Persist employee-facing AI resolution conversations."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_ai_resolution_conversations"
down_revision: Union[str, None] = "a18b7c9d2e41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_resolution_conversations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("escalation_reason", sa.String(length=80)),
        sa.Column("provider_model", sa.String(length=150)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ticket_id", name="uq_ai_resolution_conversations_ticket"),
        sa.CheckConstraint("status IN ('ACTIVE', 'ESCALATED', 'RESOLVED')", name="chk_ai_resolution_conversation_status"),
    )
    op.create_index(
        "idx_ai_resolution_conversations_status",
        "ai_resolution_conversations",
        ["status", "updated_at"],
    )

    op.create_table(
        "ai_resolution_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("speaker", sa.String(length=20), nullable=False),
        sa.Column("author_id", sa.BigInteger()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_resolution_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("speaker IN ('EMPLOYEE', 'AI')", name="chk_ai_resolution_message_speaker"),
        sa.CheckConstraint(
            "(speaker = 'AI' AND author_id IS NULL) OR (speaker = 'EMPLOYEE' AND author_id IS NOT NULL)",
            name="chk_ai_resolution_message_author",
        ),
    )
    op.create_index(
        "idx_ai_resolution_messages_conversation",
        "ai_resolution_messages",
        ["conversation_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("idx_ai_resolution_messages_conversation", table_name="ai_resolution_messages")
    op.drop_table("ai_resolution_messages")
    op.drop_index("idx_ai_resolution_conversations_status", table_name="ai_resolution_conversations")
    op.drop_table("ai_resolution_conversations")