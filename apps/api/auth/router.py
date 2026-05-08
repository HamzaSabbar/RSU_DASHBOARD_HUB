from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_admin_user, get_current_user
from auth.hashing import hash_password, verify_password
from auth.jwt import encode_access_token
from db.models import AuditLog, User
from db.session import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: str
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    user: UserPublic


class ViewerCreateRequest(BaseModel):
    email: str
    password: str
    role: Literal["viewer"] = "viewer"


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    user = await session.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    user.last_login_at = datetime.now(tz=UTC)
    session.add(AuditLog(user_id=user.id, action="login", target_type="user", target_id=user.id))
    await session.commit()

    token = encode_access_token(str(user.id), user.email, user.role)
    return LoginResponse(
        access_token=token,
        user=UserPublic(id=str(user.id), email=user.email, role=user.role),
    )


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic(id=str(user.id), email=user.email, role=user.role)


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    _admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[UserPublic]:
    users = list(await session.scalars(select(User).order_by(User.created_at.desc())))
    return [UserPublic(id=str(user.id), email=user.email, role=user.role) for user in users]


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_viewer(
    body: ViewerCreateRequest,
    admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
) -> UserPublic:
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid email")
    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="password must contain at least 8 characters",
        )

    existing = await session.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user already exists",
        )

    user = User(email=email, password_hash=hash_password(body.password), role="viewer")
    session.add(user)
    await session.flush()
    session.add(
        AuditLog(
            user_id=admin.id,
            action="create_viewer",
            target_type="user",
            target_id=user.id,
            audit_metadata={"email": email},
        )
    )
    await session.commit()
    return UserPublic(id=str(user.id), email=user.email, role=user.role)
