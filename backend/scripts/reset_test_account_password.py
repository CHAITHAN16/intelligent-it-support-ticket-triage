"""Local development utility to reset the designated test account password.

Run from the project root with DATABASE_URL available in the environment:
    python backend/scripts/reset_test_account_password.py

The new password is entered interactively and is never displayed or logged.
"""

from getpass import getpass

from sqlalchemy import select

from auth import password_hash
from database import SessionLocal
from models import User


TARGET_USER_ID = 1
TARGET_EMAIL = "test.employee@example.com"


def main() -> int:
    new_password = getpass("New password (hidden): ")
    confirmation = getpass("Confirm new password (hidden): ")

    if len(new_password) < 8:
        print("Password must be at least 8 characters long.")
        return 1
    if new_password != confirmation:
        print("Passwords do not match.")
        return 1

    db = SessionLocal()
    try:
        user = db.scalar(
            select(User).where(
                User.id == TARGET_USER_ID,
                User.email == TARGET_EMAIL,
            )
        )
        if user is None:
            db.rollback()
            print("The expected test account was not found; no changes were made.")
            return 1

        user.password_hash = password_hash.hash(new_password)
        db.commit()
    except Exception:
        db.rollback()
        print("Password reset failed; the transaction was rolled back.")
        return 1
    finally:
        db.close()

    print("Password reset committed for the expected local test account.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
