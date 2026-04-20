from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_user
from auth.hashing import verify_password
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
