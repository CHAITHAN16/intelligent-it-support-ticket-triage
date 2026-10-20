
"""merge ticket field history and user authentication

Revision ID: 644de88e41c7
Revises: 0002_ticket_field_history, 0002_user_authentication
Create Date: 2026-10-08 21:18:22.579411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '644de88e41c7'
down_revision: Union[str, None] = (
    '0002_ticket_field_history', '0002_user_authentication')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
