from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt

from config import settings


def encode_access_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.jwt_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.nextauth_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jwt.decode(token, settings.nextauth_secret, algorithms=[settings.jwt_algorithm]),
    )
