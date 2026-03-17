from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from core.config.database_config import DatabaseConfig


_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        cfg = DatabaseConfig()
        _ENGINE = create_engine(
            cfg.get_sqlalchemy_url(),
            future=True,
            pool_pre_ping=True,
        )
    return _ENGINE


def reset_engine() -> None:
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None

