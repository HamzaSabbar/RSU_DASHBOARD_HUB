from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from config import settings
from data_platform.repository import DataPlatformRepository
from db.models import User
from db.session import SessionLocal


async def enqueue(*, include_score_variables: bool) -> str:
    async with SessionLocal() as session, session.begin():
        user = await session.scalar(select(User).where(User.email == settings.admin_email))
        batch = await DataPlatformRepository(session).create_batch(
            source_key="rsu-csv",
            source_path=settings.analytics_source_path,
            pipeline_version=settings.analytics_pipeline_version,
            parameters={
                "source_key": "rsu-csv",
                "compatibility_profile": "julia-30d-v1",
                "include_score_variables": include_score_variables,
            },
            created_by=user.id if user else None,
        )
        return str(batch.id)


def main() -> None:
    parser = argparse.ArgumentParser(description="RSU data-platform operations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    enqueue_parser = subparsers.add_parser("enqueue", help="queue the configured RAW folder")
    enqueue_parser.add_argument(
        "--include-score-variables",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include the 63M-row score_variable.csv extended layer",
    )
    args = parser.parse_args()
    if args.command == "enqueue":
        batch_id = asyncio.run(
            enqueue(include_score_variables=bool(args.include_score_variables))
        )
        print(batch_id)


if __name__ == "__main__":
    main()
