from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_user
from boards.registry import discover_boards
from db.models import Board, BoardSnapshot, User
from db.session import get_session

router = APIRouter(prefix="/api/boards", tags=["boards"])


class BoardSummary(BaseModel):
    slug: str
    title: str
    description: str
    last_updated: datetime | None
    status: str  # "ready" | "no_data"


@router.get("", response_model=list[BoardSummary])
async def list_boards(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BoardSummary]:
    registry = discover_boards()
    if not registry:
        return []

    rows = await session.execute(
        select(Board.slug, Board.title, Board.description).where(
            Board.slug.in_(registry.keys())
        )
    )
    db_boards = {slug: (title, desc) for slug, title, desc in rows.all()}

    out: list[BoardSummary] = []
    for slug, spec in registry.items():
        last = await session.scalar(
            select(BoardSnapshot.computed_at)
            .join(Board, Board.id == BoardSnapshot.board_id)
            .where(Board.slug == slug)
            .order_by(BoardSnapshot.computed_at.desc())
            .limit(1)
        )
        title, description = db_boards.get(slug, (spec.title, spec.description))
        out.append(
            BoardSummary(
                slug=slug,
                title=title,
                description=description,
                last_updated=last,
                status="ready" if last else "no_data",
            )
        )
    return out
