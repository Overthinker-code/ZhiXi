"""Database readiness check used by local and deployment startup scripts."""

import logging
from pathlib import Path

import sqlmodel
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.engine import Engine

from app.core.db import engine
from app.db.base_class import Base

import app.models  # noqa: F401,E402

logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def schema_revision_status(
    connection: Connection,
    *,
    alembic_ini: Path | None = None,
) -> dict[str, object]:
    """Return whether the connected database is at every Alembic head.

    Readiness must distinguish "the database accepts SELECT 1" from "the
    schema this application expects is actually installed".  This check is
    read-only and supports repositories that may acquire multiple heads later.
    """
    config = Config(str(alembic_ini or (BACKEND_ROOT / "alembic.ini")))
    config.set_main_option("script_location", str(BACKEND_ROOT / "app" / "alembic"))
    expected_heads = tuple(sorted(ScriptDirectory.from_config(config).get_heads()))
    current_heads = tuple(
        sorted(MigrationContext.configure(connection).get_current_heads())
    )
    return {
        "status": "current" if current_heads == expected_heads else "outdated",
        "current": list(current_heads),
        "expected": list(expected_heads),
    }


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


def bootstrap_legacy_empty_database(
    db_engine: Engine = engine,
    *,
    alembic_ini: Path | None = None,
) -> bool:
    """Create and stamp only a truly empty legacy database.

    Revisions 001-006 assume tables that predated Alembic. For an empty
    PostgreSQL database, create the complete current schema and stamp head only
    when there is no version table and no business table. Existing databases
    are never stamped and must use normal ``upgrade head``.
    """
    tables = set(inspect(db_engine).get_table_names())
    if tables:
        logger.info("Existing database detected; Alembic upgrade remains authoritative")
        return False

    logger.warning(
        "Empty legacy database detected; creating current schema and stamping Alembic head"
    )
    Base.metadata.create_all(bind=db_engine)
    sqlmodel.SQLModel.metadata.create_all(bind=db_engine)
    config = Config(str(alembic_ini or (BACKEND_ROOT / "alembic.ini")))
    with db_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "head")
    logger.warning(
        "Legacy baseline bootstrap completed; a formal full baseline migration is still required"
    )
    return True


def main() -> None:
    logger.info("Checking database availability")
    init()
    bootstrap_legacy_empty_database()


if __name__ == "__main__":
    main()
