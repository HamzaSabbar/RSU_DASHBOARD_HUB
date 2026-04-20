from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth.deps import get_current_user
from db.models import User

router = APIRouter(prefix="/api/boards", tags=["boards"])


class BoardSummary(BaseModel):
    slug: str
    title: str
    description: str
    last_updated: str | None
    status: str  # "ready" | "no_data"


@router.get("", response_model=list[BoardSummary])
async def list_boards(_user: User = Depends(get_current_user)) -> list[BoardSummary]:
    # Step 4 wires this up to the board registry + snapshots join.
    return []
