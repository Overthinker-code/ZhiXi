from unittest.mock import MagicMock, patch

from sqlmodel import select

from app.backend_pre_start import (
    bootstrap_legacy_empty_database,
    init,
    logger,
    schema_revision_status,
)


def test_init_successful_connection() -> None:
    engine_mock = MagicMock()

    session_mock = MagicMock()
    exec_mock = MagicMock(return_value=True)
    session_mock.configure_mock(**{"exec.return_value": exec_mock})

    with (
        patch("sqlmodel.Session", return_value=session_mock),
        patch.object(logger, "info"),
        patch.object(logger, "error"),
        patch.object(logger, "warn"),
    ):
        try:
            init(engine_mock)
            connection_successful = True
        except Exception:
            connection_successful = False

        assert connection_successful, (
            "The database connection should be successful and not raise an exception."
        )

        session_mock.exec.assert_called_once()
        executed_statement = session_mock.exec.call_args.args[0]
        assert str(executed_statement) == str(select(1))
        session_mock.close.assert_called_once()


def test_legacy_bootstrap_only_stamps_a_truly_empty_database(tmp_path) -> None:
    engine_mock = MagicMock()
    connection_context = MagicMock()
    engine_mock.begin.return_value = connection_context
    connection_context.__enter__.return_value = MagicMock()
    inspector = MagicMock()
    inspector.get_table_names.return_value = []

    with (
        patch("app.backend_pre_start.inspect", return_value=inspector),
        patch("app.backend_pre_start.Base.metadata.create_all") as create_base,
        patch("app.backend_pre_start.sqlmodel.SQLModel.metadata.create_all") as create_sqlmodel,
        patch("app.backend_pre_start.command.stamp") as stamp,
    ):
        bootstrapped = bootstrap_legacy_empty_database(
            engine_mock,
            alembic_ini=tmp_path / "alembic.ini",
        )

    assert bootstrapped is True
    create_base.assert_called_once_with(bind=engine_mock)
    create_sqlmodel.assert_called_once_with(bind=engine_mock)
    stamp.assert_called_once()


def test_legacy_bootstrap_never_stamps_an_existing_database() -> None:
    engine_mock = MagicMock()
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["user"]

    with (
        patch("app.backend_pre_start.inspect", return_value=inspector),
        patch("app.backend_pre_start.Base.metadata.create_all") as create_base,
        patch("app.backend_pre_start.command.stamp") as stamp,
    ):
        bootstrapped = bootstrap_legacy_empty_database(engine_mock)

    assert bootstrapped is False
    create_base.assert_not_called()
    stamp.assert_not_called()


def test_schema_revision_status_requires_every_alembic_head(tmp_path) -> None:
    connection = MagicMock()
    script = MagicMock()
    script.get_heads.return_value = ["010", "feature-head"]
    migration_context = MagicMock()
    migration_context.get_current_heads.return_value = ["feature-head", "010"]

    with (
        patch(
            "app.backend_pre_start.ScriptDirectory.from_config",
            return_value=script,
        ),
        patch(
            "app.backend_pre_start.MigrationContext.configure",
            return_value=migration_context,
        ),
    ):
        result = schema_revision_status(
            connection,
            alembic_ini=tmp_path / "alembic.ini",
        )

    assert result == {
        "status": "current",
        "current": ["010", "feature-head"],
        "expected": ["010", "feature-head"],
    }

    migration_context.get_current_heads.return_value = ["010"]
    with (
        patch(
            "app.backend_pre_start.ScriptDirectory.from_config",
            return_value=script,
        ),
        patch(
            "app.backend_pre_start.MigrationContext.configure",
            return_value=migration_context,
        ),
    ):
        result = schema_revision_status(connection)

    assert result["status"] == "outdated"
    assert result["expected"] == ["010", "feature-head"]
