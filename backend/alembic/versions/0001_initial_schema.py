"""Create the initial IT support schema.

Revision ID: 0001_initial_schema
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM("EMPLOYEE", "SUPPORT_AGENT", "ADMIN", name="user_role", create_type=False)
ticket_status = postgresql.ENUM("NEW", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED", name="ticket_status", create_type=False)
ticket_priority = postgresql.ENUM("LOW", "MEDIUM", "HIGH", "URGENT", name="ticket_priority", create_type=False)
assignment_source = postgresql.ENUM("AI", "SYSTEM", "HUMAN", name="assignment_source", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (user_role, ticket_status, ticket_priority, assignment_source):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("id", "role", name="uq_users_id_role"),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_teams_name"),
    )
    op.create_table(
        "team_members",
        sa.Column("team_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("member_role", user_role, nullable=False, server_default="SUPPORT_AGENT"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("team_id", "user_id"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT", name="fk_team_member_team"),
        sa.ForeignKeyConstraint(["user_id", "member_role"], ["users.id", "users.role"], ondelete="RESTRICT", name="fk_team_member_user_role"),
        sa.CheckConstraint("member_role = 'SUPPORT_AGENT'", name="chk_team_member_role"),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("subcategory", sa.String(100)),
        sa.Column("priority", ticket_priority, nullable=False, server_default="MEDIUM"),
        sa.Column("status", ticket_status, nullable=False, server_default="NEW"),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_team_id", sa.BigInteger()),
        sa.Column("assigned_agent_id", sa.BigInteger()),
        sa.Column("ai_predicted_category", sa.String(100)),
        sa.Column("ai_predicted_subcategory", sa.String(100)),
        sa.Column("ai_predicted_priority", ticket_priority),
        sa.Column("ai_confidence", sa.Numeric(5, 4)),
        sa.Column("ai_model_version", sa.String(100)),
        sa.Column("ai_triaged_at", sa.DateTime(timezone=True)),
        sa.Column("routing_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="RESTRICT", name="fk_ticket_creator"),
        sa.ForeignKeyConstraint(["assigned_team_id"], ["teams.id"], ondelete="RESTRICT", name="fk_ticket_team"),
        sa.ForeignKeyConstraint(["assigned_agent_id"], ["users.id"], ondelete="RESTRICT", name="fk_ticket_agent"),
        sa.ForeignKeyConstraint(["assigned_team_id", "assigned_agent_id"], ["team_members.team_id", "team_members.user_id"], name="fk_ticket_agent_team_membership"),
        sa.CheckConstraint("assigned_agent_id IS NULL OR assigned_team_id IS NOT NULL", name="chk_ticket_agent_requires_team"),
        sa.CheckConstraint("ai_confidence IS NULL OR ai_confidence BETWEEN 0 AND 1", name="chk_ai_confidence"),
        sa.CheckConstraint("ai_triaged_at IS NULL OR ai_triaged_at >= created_at", name="chk_ai_triaged_timestamp"),
        sa.CheckConstraint("resolved_at IS NULL OR resolved_at >= created_at", name="chk_resolved_timestamp"),
        sa.CheckConstraint("closed_at IS NULL OR closed_at >= created_at", name="chk_closed_timestamp"),
    )
    op.create_table(
        "ticket_assignments",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.BigInteger()),
        sa.Column("agent_id", sa.BigInteger()),
        sa.Column("source", assignment_source, nullable=False),
        sa.Column("assigned_by_id", sa.BigInteger()),
        sa.Column("routing_reason", sa.Text()),
        sa.Column("model_version", sa.String(100)),
        sa.Column("ai_confidence", sa.Numeric(5, 4)),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE", name="fk_assignment_ticket"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT", name="fk_assignment_team"),
        sa.ForeignKeyConstraint(["agent_id"], ["users.id"], ondelete="RESTRICT", name="fk_assignment_agent"),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="RESTRICT", name="fk_assignment_assigned_by"),
        sa.ForeignKeyConstraint(["team_id", "agent_id"], ["team_members.team_id", "team_members.user_id"], name="fk_assignment_agent_team_membership"),
        sa.CheckConstraint("agent_id IS NULL OR team_id IS NOT NULL", name="chk_assignment_agent_requires_team"),
        sa.CheckConstraint("team_id IS NOT NULL OR agent_id IS NOT NULL", name="chk_assignment_target"),
        sa.CheckConstraint("(source = 'HUMAN' AND assigned_by_id IS NOT NULL) OR (source IN ('AI', 'SYSTEM') AND assigned_by_id IS NULL)", name="chk_assignment_source_actor"),
        sa.CheckConstraint("ai_confidence IS NULL OR ai_confidence BETWEEN 0 AND 1", name="chk_assignment_ai_confidence"),
        sa.CheckConstraint("unassigned_at IS NULL OR unassigned_at >= assigned_at", name="chk_assignment_dates"),
    )
    op.create_table(
        "ticket_status_history",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("old_status", ticket_status),
        sa.Column("new_status", ticket_status, nullable=False),
        sa.Column("changed_by_id", sa.BigInteger()),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE", name="fk_status_history_ticket"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="RESTRICT", name="fk_status_history_user"),
        sa.CheckConstraint("old_status IS NULL OR old_status <> new_status", name="chk_status_changed"),
    )
    op.create_table(
        "comments",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE", name="fk_comment_ticket"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT", name="fk_comment_author"),
    )

    indexes = (
        ("idx_users_role", "users", ["role"], {}),
        ("idx_team_members_user", "team_members", ["user_id"], {}),
        ("idx_tickets_creator", "tickets", ["creator_id"], {}),
        ("idx_tickets_status_priority", "tickets", ["status", "priority"], {}),
        ("idx_tickets_category", "tickets", ["category", "subcategory"], {}),
        ("idx_tickets_assigned_team", "tickets", ["assigned_team_id"], {}),
        ("idx_tickets_assigned_agent", "tickets", ["assigned_agent_id"], {}),
        ("idx_tickets_created_at", "tickets", ["created_at"], {}),
        ("idx_ticket_assignments_ticket", "ticket_assignments", ["ticket_id", "assigned_at"], {}),
        ("idx_ticket_assignments_active", "ticket_assignments", ["ticket_id"], {"postgresql_where": sa.text("unassigned_at IS NULL")}),
        ("idx_ticket_assignments_agent", "ticket_assignments", ["agent_id", "assigned_at"], {}),
        ("idx_ticket_assignments_team", "ticket_assignments", ["team_id", "assigned_at"], {}),
        ("idx_ticket_assignments_source", "ticket_assignments", ["source", "assigned_at"], {}),
        ("idx_ticket_status_history_ticket", "ticket_status_history", ["ticket_id", "changed_at"], {}),
        ("idx_comments_ticket", "comments", ["ticket_id", "created_at"], {}),
    )
    for name, table, columns, kwargs in indexes:
        op.create_index(name, table, columns, **kwargs)


def downgrade() -> None:
    for name, table, _, _ in (
        ("idx_comments_ticket", "comments", None, None),
        ("idx_ticket_status_history_ticket", "ticket_status_history", None, None),
        ("idx_ticket_assignments_source", "ticket_assignments", None, None),
        ("idx_ticket_assignments_team", "ticket_assignments", None, None),
        ("idx_ticket_assignments_agent", "ticket_assignments", None, None),
        ("idx_ticket_assignments_active", "ticket_assignments", None, None),
        ("idx_ticket_assignments_ticket", "ticket_assignments", None, None),
        ("idx_tickets_created_at", "tickets", None, None),
        ("idx_tickets_assigned_agent", "tickets", None, None),
        ("idx_tickets_assigned_team", "tickets", None, None),
        ("idx_tickets_category", "tickets", None, None),
        ("idx_tickets_status_priority", "tickets", None, None),
        ("idx_tickets_creator", "tickets", None, None),
        ("idx_team_members_user", "team_members", None, None),
        ("idx_users_role", "users", None, None),
    ):
        op.drop_index(name, table_name=table)
    for table in ("comments", "ticket_status_history", "ticket_assignments", "tickets", "team_members", "teams", "users"):
        op.drop_table(table)
    bind = op.get_bind()
    for enum in (assignment_source, ticket_priority, ticket_status, user_role):
        enum.drop(bind, checkfirst=True)
