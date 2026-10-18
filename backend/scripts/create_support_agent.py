"""Provision a support-agent account for local development only.

Run from the project root with DATABASE_URL available:
    python backend/scripts/create_support_agent.py --email agent@example.test --name "Local Agent"

The password is entered interactively and is never displayed or logged. This is
an administrative development utility, not a production account-provisioning
workflow. Existing email addresses are rejected without changes.
"""

from __future__ import annotations

import argparse
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import password_hash
from database import SessionLocal
from models import Team, TeamMember, User, UserRole


def create_support_agent(
    db: Session,
    *,
    email: str,
    name: str,
    password: str,
    team_name: str | None = None,
) -> User:
    normalized_email = email.strip().lower()
    normalized_name = name.strip()
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("A valid email address is required.")
    if not normalized_name:
        raise ValueError("A name is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if db.scalar(select(User).where(User.email == normalized_email)) is not None:
        raise ValueError("An account with that email already exists; no changes were made.")

    team = None
    if team_name is not None:
        team = db.scalar(select(Team).where(Team.name == team_name.strip()))
        if team is None:
            raise ValueError(f"Team {team_name!r} was not found; no changes were made.")

    user = User(
        name=normalized_name,
        email=normalized_email,
        password_hash=password_hash.hash(password),
        role=UserRole.SUPPORT_AGENT,
        active=True,
    )
    db.add(user)
    try:
        db.flush()
        if team is not None:
            db.add(TeamMember(team_id=team.id, user_id=user.id, member_role=UserRole.SUPPORT_AGENT))
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise ValueError("The account could not be created; verify the email and team, then retry.") from None
    except Exception:
        db.rollback()
        raise
    return user


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local development support-agent account.")
    parser.add_argument("--email", required=True, help="Email address for the new agent")
    parser.add_argument("--name", required=True, help="Display name for the new agent")
    parser.add_argument("--team", dest="team_name", help="Optional exact name of an existing team")
    args = parser.parse_args()

    password = getpass("Agent password (hidden): ")
    confirmation = getpass("Confirm password (hidden): ")
    if password != confirmation:
        print("Passwords do not match.")
        return 1

    db = SessionLocal()
    try:
        user = create_support_agent(
            db,
            email=args.email,
            name=args.name,
            password=password,
            team_name=args.team_name,
        )
    except ValueError as error:
        print(error)
        return 1
    except Exception:
        print("Support-agent account creation failed; the transaction was rolled back.")
        return 1
    finally:
        db.close()

    print(f"Created local support-agent account for {user.email} (user ID {user.id}).")
    if args.team_name:
        print(f"Added the agent to team {args.team_name!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
