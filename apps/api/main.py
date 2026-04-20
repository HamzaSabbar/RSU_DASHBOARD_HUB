from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from auth.hashing import hash_password
from auth.router import router as auth_router
from boards.router import router as boards_router
from config import settings
from db.models import Board, User
from db.session import SessionLocal

logger = logging.getLogger("uvicorn.error")

BOARDS_SEED: list[dict[str, Any]] = [
    {
        "slug": "macro-national",
        "title": "Macro National",
        "description": (
            "Tableau de bord hebdomadaire de suivi RSU: inscriptions, "
            "traitement FMS, flux ASD, ménages bloqués."
        ),
    },
]


async def _seed() -> None:
    async with SessionLocal() as session:
        existing = await session.scalar(
            select(User).where(User.email == settings.admin_email)
        )
        if existing is None:
            session.add(
                User(
                    email=settings.admin_email,
                    password_hash=hash_password(settings.admin_password),
                    role="admin",
                )
            )
            logger.info("Seeded admin user %s", settings.admin_email)

        for board in BOARDS_SEED:
            stmt = (
                pg_insert(Board)
                .values(**board)
                .on_conflict_do_nothing(index_elements=["slug"])
            )
            await session.execute(stmt)

        await session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await _seed()
    yield


app = FastAPI(
    title="RSU Dashboard Hub API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(boards_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
