# Backend test database safety

Run backend tests from `code/backend` with the project virtual environment:

```bash
../.venv/bin/pytest
```

Pytest never uses the database named by the development `code/.env` directly.
Before importing the application, the root `conftest.py` changes `POSTGRES_DB`
to a test-only name. By default, `zhixi` becomes a per-process database such as
`zhixi_test_p12345`. It is created before collection and dropped after all
fixtures close. The configured PostgreSQL user therefore needs `CREATEDB`
permission.

An empty test database is initialized and stamped through the same schema
bootstrap used by the application before test fixtures seed data. If a
test-only database contains a partial schema without `alembic_version`, pytest
fails fast and prints a `dropdb <test-db>` recovery command instead of applying
ambiguous migrations.

To choose the test database prefix explicitly:

```bash
ZHIXI_TEST_POSTGRES_DB=zhixi_test ../.venv/bin/pytest
```

The process suffix still applies. Set `ZHIXI_TEST_DB_REUSE=1` only when a CI
job provisions and cleans a fixed test database itself; reused databases are
not dropped by pytest.

To prohibit automatic database creation (recommended in CI):

```bash
ZHIXI_TEST_POSTGRES_DB=zhixi_test \
ZHIXI_TEST_DB_AUTO_CREATE=0 \
../.venv/bin/pytest
```

The name must start with `test_` or contain `_test`. Pytest fails before the
application engine is imported if the name is unsafe, matches the development
database, cannot be created, or does not exist while auto-creation is disabled.
For parallel `pytest-xdist` runs, each worker receives its own suffixed test
database. Per-process databases also prevent two local pytest commands from
deleting or changing each other's data.

The nested test fixture also removes `ResourceGenerationRun` and its dependent
step/evidence/link rows before and after every test. A failed or interrupted
test therefore cannot leave an active run that blocks a later test.
