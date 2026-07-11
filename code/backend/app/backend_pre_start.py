"""Database readiness check used by local and deployment startup scripts."""

import logging

import sqlmodel
from sqlalchemy.engine import Engine

from app.core.db import engine

logger = logging.getLogger(__name__)


def init(db_engine: Engine = engine) -> None:
    """Fail fast when the configured database cannot accept a simple query."""
    session = sqlmodel.Session(db_engine)
    try:
        session.exec(sqlmodel.select(1))
        logger.info("Database connection is ready")
    except Exception:
        logger.exception("Database readiness check failed")
        raise
    finally:
        session.close()


def main() -> None:
    logger.info("Checking database availability")
    init()


if __name__ == "__main__":
    main()
