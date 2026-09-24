from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, password_hash, to_api_role, to_model_role, verify_password
from database import get_db
from models import User
from schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from auth import AuthRole


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=to_api_role(user.role),
        active=user.active,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an employee account",
    description="Create an employee account using the supplied name, email, and password. Email addresses are normalized to lowercase.",
    response_description="The new account's public profile.",
    responses={409: {"description": "An account with this email address already exists."}, 422: {"description": "The request body failed validation."}},
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    email = payload.email.lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=password_hash.hash(payload.password),
        role=to_model_role(AuthRole.EMPLOYEE),
        active=True,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from None
    return _user_response(user)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in",
    description="Validate account credentials and return a bearer access token with the user's public profile.",
    response_description="The access token and authenticated user's profile.",
    responses={401: {"description": "The credentials are invalid or the account is inactive."}, 422: {"description": "The request body failed validation."}},
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LoginResponse(access_token=create_access_token(user), user=_user_response(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user",
    description="Return the public profile associated with the bearer access token.",
    response_description="The authenticated user's profile.",
    responses={401: {"description": "The access token is missing or invalid."}},
)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(current_user)
