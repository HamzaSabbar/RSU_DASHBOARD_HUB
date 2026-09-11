from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from auth.hashing import hash_password
from auth.router import router as auth_router
from config import settings
from db.models import User
from db.session import SessionLocal
from kpi.router import router as kpi_router

logger = logging.getLogger("uvicorn.error")


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

        await session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await _seed()
    yield


app = FastAPI(
    title="RSU KPI Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(kpi_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
