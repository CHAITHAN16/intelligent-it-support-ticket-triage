"""Add curated knowledge articles and ticket solution recommendations.

Revision ID: a18b7c9d2e41
Revises: 644de88e41c7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a18b7c9d2e41"
down_revision: Union[str, None] = "644de88e41c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_articles",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("resolution_steps", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_knowledge_base_articles_active_category", "knowledge_base_articles", ["active", "category"])
    op.add_column("tickets", sa.Column("solution_status", sa.String(30)))
    op.add_column("tickets", sa.Column("suggested_solution", sa.Text()))
    op.add_column("tickets", sa.Column("knowledge_article_id", sa.BigInteger()))
    op.add_column("tickets", sa.Column("solution_confidence", sa.Numeric(5, 4)))
    op.create_foreign_key(
        "fk_tickets_knowledge_article", "tickets", "knowledge_base_articles",
        ["knowledge_article_id"], ["id"], ondelete="SET NULL",
    )
    op.create_check_constraint(
        "chk_ticket_solution_confidence", "tickets",
        "solution_confidence IS NULL OR solution_confidence BETWEEN 0 AND 1",
    )


def downgrade() -> None:
    op.drop_constraint("chk_ticket_solution_confidence", "tickets", type_="check")
    op.drop_constraint("fk_tickets_knowledge_article", "tickets", type_="foreignkey")
    op.drop_column("tickets", "solution_confidence")
    op.drop_column("tickets", "knowledge_article_id")
    op.drop_column("tickets", "suggested_solution")
    op.drop_column("tickets", "solution_status")
    op.drop_index("idx_knowledge_base_articles_active_category", table_name="knowledge_base_articles")
    op.drop_table("knowledge_base_articles")
