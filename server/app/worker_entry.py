from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.summary_worker import process_one_summary_task


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    Base.metadata.create_all(bind=engine)
    while True:
        with SessionLocal() as db:
            processed = process_one_summary_task(db)
        if not processed:
            time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
