"""Add password hashes and active status to users."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_user_authentication"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False))


def downgrade() -> None:
    op.drop_column("users", "active")
    op.drop_column("users", "password_hash")
