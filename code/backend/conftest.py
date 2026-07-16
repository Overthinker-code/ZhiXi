"""Pytest bootstrap that prevents tests from ever using the development database.

This file lives at the pytest root so it is imported before ``app`` (and the
module-level SQLAlchemy engine) is imported by the nested test fixtures.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg
import pytest
from dotenv import dotenv_values
from psycopg import sql


BACKEND_ROOT = Path(__file__).resolve().parent
ENV_FILE = BACKEND_ROOT.parent / ".env"


def _configured_value(name: str, file_values: dict[str, object]) -> str:
    value = os.getenv(name) or file_values.get(name)
    return str(value or "").strip()


def _looks_like_test_database(name: str) -> bool:
    normalized = name.lower()
    return (
        normalized.startswith("test_")
        or normalized.endswith("_test")
        or "_test_" in normalized
    )


def _safe_database_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", name)[:63]
    if not normalized or not _looks_like_test_database(normalized):
        raise pytest.UsageError(
            "Refusing to run database tests: the test database name must start "
            "with 'test_' or contain/end with '_test'. Set "
            "ZHIXI_TEST_POSTGRES_DB=zhixi_test."
        )
    return normalized


def _ensure_test_database() -> tuple[str, bool]:
    file_values = dict(dotenv_values(ENV_FILE)) if ENV_FILE.exists() else {}
    configured_db = _configured_value("POSTGRES_DB", file_values)
    development_db = str(file_values.get("POSTGRES_DB") or "").strip()
    if not configured_db:
        raise pytest.UsageError(
            "POSTGRES_DB is not configured. Configure code/.env, then set "
            "ZHIXI_TEST_POSTGRES_DB=zhixi_test before running pytest."
        )

    requested_db = os.getenv("ZHIXI_TEST_POSTGRES_DB", "").strip()
    if requested_db:
        test_db = _safe_database_name(requested_db)
    elif _looks_like_test_database(configured_db):
        test_db = _safe_database_name(configured_db)
    else:
        test_db = _safe_database_name(f"{configured_db}_test")

    reuse_database = os.getenv("ZHIXI_TEST_DB_REUSE", "0") == "1"
    if not reuse_database:
        worker = os.getenv("PYTEST_XDIST_WORKER", "").strip()
        suffix = f"_{worker}" if worker and worker != "master" else ""
        test_db = _safe_database_name(f"{test_db}{suffix}_p{os.getpid()}")

    if development_db and test_db == development_db:
        raise pytest.UsageError(
            f"Refusing to run pytest against development database '{development_db}'. "
            "Set ZHIXI_TEST_POSTGRES_DB to a distinct test-only database."
        )

    os.environ["POSTGRES_DB"] = test_db
    if os.getenv("ZHIXI_SKIP_DB_TEST_FIXTURE") == "1":
        return test_db, False

    connection_args = {
        "host": _configured_value("POSTGRES_SERVER", file_values) or "127.0.0.1",
        "port": int(_configured_value("POSTGRES_PORT", file_values) or "5432"),
        "user": _configured_value("POSTGRES_USER", file_values),
        "password": _configured_value("POSTGRES_PASSWORD", file_values),
        "dbname": os.getenv("ZHIXI_TEST_POSTGRES_MAINTENANCE_DB", "postgres"),
        "connect_timeout": 5,
    }
    auto_create = os.getenv("ZHIXI_TEST_DB_AUTO_CREATE", "1") != "0"
    try:
        with psycopg.connect(**connection_args, autocommit=True) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (test_db,)
            ).fetchone()
            if not exists:
                if not auto_create:
                    raise pytest.UsageError(
                        f"Test database '{test_db}' does not exist and automatic creation "
                        "is disabled. Create it with: createdb "
                        f"-h {connection_args['host']} -p {connection_args['port']} "
                        f"-U {connection_args['user']} {test_db}"
                    )
                connection.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_db))
                )
    except pytest.UsageError:
        raise
    except Exception as exc:
        raise pytest.UsageError(
            f"Could not prepare isolated test database '{test_db}': {exc}. "
            "Create it explicitly with: createdb "
            f"-h {connection_args['host']} -p {connection_args['port']} "
            f"-U {connection_args['user']} {test_db}; then rerun pytest. "
            "The development database was not touched."
        ) from exc
    return test_db, not reuse_database


TEST_DATABASE_NAME, EPHEMERAL_TEST_DATABASE = _ensure_test_database()


def _bootstrap_test_schema() -> None:
    if os.getenv("ZHIXI_SKIP_DB_TEST_FIXTURE") == "1":
        return

    # Import only after POSTGRES_DB has been replaced above. This uses the same
    # production bootstrap path, but exclusively against the guarded test DB.
    from sqlalchemy import inspect

    from app.backend_pre_start import bootstrap_legacy_empty_database
    from app.core.db import engine

    tables = set(inspect(engine).get_table_names())
    if not tables:
        bootstrap_legacy_empty_database(engine)
        return
    if "alembic_version" not in tables:
        raise pytest.UsageError(
            f"Test database '{TEST_DATABASE_NAME}' contains an incomplete schema "
            "without alembic_version. It is safe to rebuild this test-only database: "
            f"dropdb {TEST_DATABASE_NAME}; then rerun pytest. The development "
            "database will not be changed."
        )


_bootstrap_test_schema()


def pytest_report_header() -> str:
    return f"database isolation: PostgreSQL database={TEST_DATABASE_NAME}"


def pytest_sessionfinish() -> None:
    """Drop the per-process test database after all fixture sessions close."""
    if not EPHEMERAL_TEST_DATABASE:
        return
    from app.core.db import engine

    engine.dispose()
    file_values = dict(dotenv_values(ENV_FILE)) if ENV_FILE.exists() else {}
    with psycopg.connect(
        host=_configured_value("POSTGRES_SERVER", file_values) or "127.0.0.1",
        port=int(_configured_value("POSTGRES_PORT", file_values) or "5432"),
        user=_configured_value("POSTGRES_USER", file_values),
        password=_configured_value("POSTGRES_PASSWORD", file_values),
        dbname=os.getenv("ZHIXI_TEST_POSTGRES_MAINTENANCE_DB", "postgres"),
        autocommit=True,
        connect_timeout=5,
    ) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(TEST_DATABASE_NAME)
            )
        )
