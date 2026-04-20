from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from auth.deps import get_current_user
from boards.macro_national.schemas import EMPTY_PAYLOAD, MacroNationalPayload
from db.models import User

router = APIRouter(tags=["macro-national"])


@router.get("/data", response_model=MacroNationalPayload)
async def get_data(
    reporting_date: date | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> MacroNationalPayload:
    # Step 5+ will read the latest BoardSnapshot for this reporting_date.
    _ = reporting_date
    return EMPTY_PAYLOAD
