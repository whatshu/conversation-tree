from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.db.bootstrap import ensure_database_ready
from app.db.session import SessionLocal
from app.services.summary_worker import process_one_summary_task


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    ensure_database_ready()
    while True:
        with SessionLocal() as db:
            processed = process_one_summary_task(db)
        if not processed:
            time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
