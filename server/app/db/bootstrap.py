from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.db.base import Base
from app.db.session import engine


def ensure_database_ready() -> None:
    """Prefer Alembic migrations, but keep metadata fallback for local dev/tests."""
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    if alembic_ini.exists():
        config = Config(str(alembic_ini))
        config.set_main_option("script_location", str(alembic_ini.parent / "migrations"))
        command.upgrade(config, "head")
        return
    Base.metadata.create_all(bind=engine)
