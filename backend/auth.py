from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from enum import Enum

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserRole


class AuthRole(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    AGENT = "AGENT"
    ADMIN = "ADMIN"


JWT_ALGORITHM = "HS256"


def load_jwt_secret(configured_secret: str | None, environment: str) -> str:
    """Validate JWT configuration without including secret values in errors."""
    normalized_environment = environment.strip().lower()
    if normalized_environment not in {"development", "test", "production"}:
        raise RuntimeError("APP_ENV must be development, test, or production")

    if configured_secret is None or not configured_secret.strip():
        raise RuntimeError("JWT_SECRET_KEY must be configured; no fallback key is used")

    secret = configured_secret.strip()
    normalized_secret = secret.lower()
    placeholder_values = {
        "secret",
        "changeme",
        "change-me",
        "your-secret-key",
        "replace-with-a-local-development-secret",
    }
    if (
        normalized_secret in placeholder_values
        or normalized_secret.startswith(("replace-", "change-", "your-", "<", "${"))
        or "example" in normalized_secret
    ):
        raise RuntimeError("JWT_SECRET_KEY must be a real configured secret, not a placeholder")

    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 bytes")
    return secret


APP_ENV = os.getenv("APP_ENV", "production")
JWT_SECRET_KEY = load_jwt_secret(os.getenv("JWT_SECRET_KEY"), APP_ENV)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def to_api_role(role: UserRole) -> AuthRole:
    return AuthRole.AGENT if role == UserRole.SUPPORT_AGENT else AuthRole(role.value)


def to_model_role(role: AuthRole) -> UserRole:
    return UserRole.SUPPORT_AGENT if role == AuthRole.AGENT else UserRole(role.value)


def create_access_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "role": to_api_role(user.role).value, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub", ""))
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise credentials_error from None

    user = db.get(User, user_id)
    if user is None or not user.active:
        raise credentials_error
    return user


def require_roles(*roles: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


require_employee = require_roles(UserRole.EMPLOYEE)
require_agent = require_roles(UserRole.SUPPORT_AGENT, UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    try:
        return password_hash.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False
