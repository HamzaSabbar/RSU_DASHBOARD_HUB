from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from boards.macro_national import analytics, parser
from boards.macro_national.schemas import FileKind, MacroNationalPayload
from config import settings
from db.models import AuditLog, Board, BoardSnapshot, Upload, User

BOARD_SLUG = "macro-national"


async def _get_board_id(session: AsyncSession) -> uuid.UUID:
    board_id = await session.scalar(select(Board.id).where(Board.slug == BOARD_SLUG))
    if board_id is None:
        raise RuntimeError(f"board {BOARD_SLUG!r} missing from db")
    return board_id


async def persist_upload(
    session: AsyncSession,
    *,
    user: User,
    original_filename: str,
    content: bytes,
) -> tuple[Upload, str | None]:
    """Write a file to disk and record a uploads row. Returns (row, error_message)."""
    board_id = await _get_board_id(session)

    target_dir: Path = settings.upload_dir / BOARD_SLUG
    target_dir.mkdir(parents=True, exist_ok=True)

    file_kind = parser.detect_file_kind(original_filename, content)
    row_count: int | None = None
    error: str | None = None

    if file_kind is None:
        error = "type de fichier non reconnu"
    elif file_kind == FileKind.INSCRIPTIONS_RNP:
        try:
            df = parser.parse_inscriptions_rnp(content)
            row_count = int(df.shape[0])
        except Exception as exc:  # noqa: BLE001
            error = f"parse inscriptions: {exc}"
    else:
        error = f"parseur non encore implémenté pour {file_kind.value}"

    stored_name = f"{uuid.uuid4()}_{original_filename}"
    stored_path = target_dir / stored_name
    stored_path.write_bytes(content)

    status = "accepted" if error is None else "rejected"
    upload = Upload(
        board_id=board_id,
        file_kind=file_kind.value if file_kind else "unknown",
        original_filename=original_filename,
        stored_path=str(stored_path),
        uploaded_by=user.id,
        row_count=row_count,
        status=status,
        error_message=error,
    )
    session.add(upload)
    session.add(
        AuditLog(
            user_id=user.id,
            action="upload",
            target_type="board",
            target_id=board_id,
            audit_metadata={
                "file_kind": upload.file_kind,
                "status": status,
                "original_filename": original_filename,
            },
        )
    )
    return upload, error


async def recompute_snapshot(session: AsyncSession, *, user: User) -> MacroNationalPayload:
    """Read the latest accepted upload per file_kind, run analytics, upsert snapshot."""
    board_id = await _get_board_id(session)

    # latest accepted upload per file_kind
    sub = (
        select(Upload.file_kind, Upload.stored_path, Upload.uploaded_at)
        .where(Upload.board_id == board_id, Upload.status == "accepted")
        .order_by(Upload.file_kind, Upload.uploaded_at.desc())
    )
    rows = (await session.execute(sub)).all()
    latest_by_kind: dict[str, str] = {}
    for kind, path, _ in rows:
        latest_by_kind.setdefault(kind, path)

    payload = MacroNationalPayload()

    inscriptions_path = latest_by_kind.get(FileKind.INSCRIPTIONS_RNP.value)
    if inscriptions_path:
        content = Path(inscriptions_path).read_bytes()
        df = parser.parse_inscriptions_rnp(content)
        payload.inscriptions_kpis = analytics.compute_inscriptions_kpis(df)
        payload.monthly_evolution = analytics.compute_monthly_evolution(df)
        payload.top_provinces_inscriptions = analytics.compute_top_provinces(df, k=5)

    payload.reporting_date = date.today().isoformat()

    today = date.today()
    stmt = (
        pg_insert(BoardSnapshot)
        .values(
            board_id=board_id,
            reporting_date=today,
            payload=payload.model_dump(mode="json"),
            computed_by=user.id,
            computed_at=datetime.now(tz=UTC),
        )
        .on_conflict_do_update(
            index_elements=["board_id", "reporting_date"],
            set_={
                "payload": payload.model_dump(mode="json"),
                "computed_at": datetime.now(tz=UTC),
                "computed_by": user.id,
            },
        )
    )
    await session.execute(stmt)
    session.add(
        AuditLog(
            user_id=user.id,
            action="snapshot",
            target_type="board",
            target_id=board_id,
            audit_metadata={"reporting_date": today.isoformat()},
        )
    )
    return payload


async def get_latest_payload(
    session: AsyncSession, *, on_or_before: date | None
) -> MacroNationalPayload:
    board_id = await _get_board_id(session)
    stmt = (
        select(BoardSnapshot.payload)
        .where(BoardSnapshot.board_id == board_id)
        .order_by(BoardSnapshot.reporting_date.desc())
        .limit(1)
    )
    if on_or_before is not None:
        stmt = (
            select(BoardSnapshot.payload)
            .where(
                BoardSnapshot.board_id == board_id,
                BoardSnapshot.reporting_date <= on_or_before,
            )
            .order_by(BoardSnapshot.reporting_date.desc())
            .limit(1)
        )
    raw = await session.scalar(stmt)
    if raw is None:
        return MacroNationalPayload()
    return MacroNationalPayload.model_validate(raw)
