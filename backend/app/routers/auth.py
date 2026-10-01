import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth import (
    create_access_token,
    get_current_user,
    get_user_by_email,
    hash_password,
    verify_password,
)
from app.config import settings
from app.database import get_session
from app.models import Role, User
from app.schemas import Token, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, session: Session = Depends(get_session)) -> Token:
    if payload.role == Role.teacher:
        _check_admin_signup_code(payload.signup_code)

    email = payload.email.lower().strip()
    if get_user_by_email(session, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return Token(access_token=create_access_token(user), user=UserRead.model_validate(user))


def _check_admin_signup_code(code: str | None) -> None:
    """Admin accounts can see every student's work, so they are never open signup."""
    expected = settings.admin_signup_code
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin registration is disabled on this server.",
        )
    if not code or not secrets.compare_digest(code.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin signup code.",
        )


@router.post("/login", response_model=Token)
def login(payload: UserLogin, session: Session = Depends(get_session)) -> Token:
    user = get_user_by_email(session, payload.email.lower().strip())
    # Same message either way, so the endpoint can't be used to enumerate accounts.
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    return Token(access_token=create_access_token(user), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user
