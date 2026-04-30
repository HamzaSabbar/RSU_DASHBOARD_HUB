from __future__ import annotations

import asyncio
import logging

from config import settings
from reports import service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("reports.worker")


async def run_worker() -> None:
    poll_seconds = max(1.0, float(settings.report_worker_poll_seconds))
    logger.info("Report worker started; polling every %.1fs", poll_seconds)
    while True:
        processed = await service.process_next_report_job()
        if not processed:
            await asyncio.sleep(poll_seconds)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
