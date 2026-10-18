import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from auth import password_hash, verify_password
from models import Base, Team, TeamMember, User, UserRole
from routers.auth import register
from schemas.auth import RegisterRequest
from scripts.create_support_agent import create_support_agent


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_create_support_agent_persists_support_agent_and_hashes_password(db_session):
    agent = create_support_agent(
        db_session,
        email="  Agent@Example.Test ",
        name=" Local Agent ",
        password="a-strong-local-password",
    )

    assert agent.email == "agent@example.test"
    assert agent.name == "Local Agent"
    assert agent.role == UserRole.SUPPORT_AGENT
    assert agent.password_hash != "a-strong-local-password"
    assert verify_password("a-strong-local-password", agent.password_hash)


def test_create_support_agent_can_assign_existing_team(db_session):
    db_session.add(Team(id=1, name="Network Infrastructure"))
    db_session.commit()

    agent = create_support_agent(
        db_session,
        email="agent@example.test",
        name="Local Agent",
        password="a-strong-local-password",
        team_name="Network Infrastructure",
    )

    membership = db_session.scalar(select(TeamMember).where(TeamMember.user_id == agent.id))
    assert membership is not None
    assert membership.team_id == 1
    assert membership.member_role == UserRole.SUPPORT_AGENT


def test_create_support_agent_rejects_duplicate_email_without_modifying_existing_user(db_session):
    existing = User(
        id=12,
        name="Existing Employee",
        email="agent@example.test",
        role=UserRole.EMPLOYEE,
        password_hash=password_hash.hash("existing-password"),
    )
    db_session.add(existing)
    db_session.commit()
    old_hash = existing.password_hash

    with pytest.raises(ValueError, match="already exists"):
        create_support_agent(
            db_session,
            email="AGENT@example.test",
            name="Should Not Replace",
            password="another-strong-password",
        )

    db_session.refresh(existing)
    assert existing.role == UserRole.EMPLOYEE
    assert existing.password_hash == old_hash
    assert db_session.scalar(select(User).where(User.email == "agent@example.test")).id == existing.id


def test_employee_registration_remains_employee(db_session):
    response = register(
        RegisterRequest(name="Registered Employee", email="employee@example.test", password="employee-password"),
        db_session,
    )

    assert response.role.value == "EMPLOYEE"
    assert db_session.get(User, response.id).role == UserRole.EMPLOYEE
