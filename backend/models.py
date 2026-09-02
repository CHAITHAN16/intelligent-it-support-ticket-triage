from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    ADMIN = "ADMIN"


class TicketStatus(str, Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class AssignmentSource(str, Enum):
    AI = "AI"
    SYSTEM = "SYSTEM"
    HUMAN = "HUMAN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("id", "role", name="uq_users_id_role"),)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    member_role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role", create_type=False), nullable=False, default=UserRole.SUPPORT_AGENT
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["user_id", "member_role"], ["users.id", "users.role"], ondelete="RESTRICT", name="fk_team_member_user_role"),
        CheckConstraint("member_role = 'SUPPORT_AGENT'", name="chk_team_member_role"),
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    subcategory: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[TicketPriority] = mapped_column(SqlEnum(TicketPriority, name="ticket_priority"), nullable=False, default=TicketPriority.MEDIUM, server_default="MEDIUM")
    status: Mapped[TicketStatus] = mapped_column(SqlEnum(TicketStatus, name="ticket_status"), nullable=False, default=TicketStatus.NEW, server_default="NEW")
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assigned_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"))
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    ai_predicted_category: Mapped[str | None] = mapped_column(String(100))
    ai_predicted_subcategory: Mapped[str | None] = mapped_column(String(100))
    ai_predicted_priority: Mapped[TicketPriority | None] = mapped_column(SqlEnum(TicketPriority, name="ticket_priority", create_type=False))
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    ai_model_version: Mapped[str | None] = mapped_column(String(100))
    ai_triaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    routing_reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        ForeignKeyConstraint(["assigned_team_id", "assigned_agent_id"], ["team_members.team_id", "team_members.user_id"], name="fk_ticket_agent_team_membership"),
        CheckConstraint("assigned_agent_id IS NULL OR assigned_team_id IS NOT NULL", name="chk_ticket_agent_requires_team"),
        CheckConstraint("ai_confidence IS NULL OR ai_confidence BETWEEN 0 AND 1", name="chk_ai_confidence"),
        CheckConstraint("ai_triaged_at IS NULL OR ai_triaged_at >= created_at", name="chk_ai_triaged_timestamp"),
        CheckConstraint("resolved_at IS NULL OR resolved_at >= created_at", name="chk_resolved_timestamp"),
        CheckConstraint("closed_at IS NULL OR closed_at >= created_at", name="chk_closed_timestamp"),
        Index("idx_tickets_status_priority", "status", "priority"),
        Index("idx_tickets_category", "category", "subcategory"),
        Index("idx_tickets_created_at", "created_at"),
    )


class TicketAssignment(Base):
    __tablename__ = "ticket_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    source: Mapped[AssignmentSource] = mapped_column(SqlEnum(AssignmentSource, name="assignment_source"), nullable=False)
    assigned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    routing_reason: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(100))
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        ForeignKeyConstraint(["team_id", "agent_id"], ["team_members.team_id", "team_members.user_id"], name="fk_assignment_agent_team_membership"),
        CheckConstraint("agent_id IS NULL OR team_id IS NOT NULL", name="chk_assignment_agent_requires_team"),
        CheckConstraint("team_id IS NOT NULL OR agent_id IS NOT NULL", name="chk_assignment_target"),
        CheckConstraint("(source = 'HUMAN' AND assigned_by_id IS NOT NULL) OR (source IN ('AI', 'SYSTEM') AND assigned_by_id IS NULL)", name="chk_assignment_source_actor"),
        CheckConstraint("ai_confidence IS NULL OR ai_confidence BETWEEN 0 AND 1", name="chk_assignment_ai_confidence"),
        CheckConstraint("unassigned_at IS NULL OR unassigned_at >= assigned_at", name="chk_assignment_dates"),
        Index("idx_ticket_assignments_ticket", "ticket_id", "assigned_at"),
        Index("idx_ticket_assignments_active", "ticket_id", postgresql_where=(unassigned_at.is_(None))),
    )


class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    old_status: Mapped[TicketStatus | None] = mapped_column(SqlEnum(TicketStatus, name="ticket_status", create_type=False))
    new_status: Mapped[TicketStatus] = mapped_column(SqlEnum(TicketStatus, name="ticket_status", create_type=False), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("old_status IS NULL OR old_status <> new_status", name="chk_status_changed"),
        Index("idx_ticket_status_history_ticket", "ticket_id", "changed_at"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_comments_ticket", "ticket_id", "created_at"),)
