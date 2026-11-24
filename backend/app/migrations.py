"""Programmatic Alembic upgrade, run at startup (single-instance deployment)."""

from __future__ import annotations

from alembic.config import Config

from alembic import command
from app.config import BACKEND_DIR, get_settings


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    cfg.attributes["configure_logger"] = False
    return cfg


def upgrade_to_head() -> None:
    command.upgrade(alembic_config(), "head")
