from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from enum import Enum

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserRole


class AuthRole(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    AGENT = "AGENT"
    ADMIN = "ADMIN"


JWT_ALGORITHM = "HS256"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "local-development-secret-change-me")
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
    return bool(hashed_password) and password_hash.verify(plain_password, hashed_password)

