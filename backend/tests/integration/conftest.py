import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

SKIP_REASON = "TEST_DATABASE_URL is not set; PostgreSQL integration tests are skipped"


@pytest.fixture(scope="session")
def test_database_url() -> str:
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip(SKIP_REASON)

    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL")
    if not url.database or "test" not in url.database.lower():
        pytest.fail("TEST_DATABASE_URL must identify a dedicated test database")
    return raw_url


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    return Config(str(backend_root / "alembic.ini"))


@pytest.fixture(scope="session")
def integration_engine(
    test_database_url: str,
    alembic_config: Config,
) -> Iterator[Engine]:
    reset_engine = create_engine(
        test_database_url,
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )
    try:
        with reset_engine.connect() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            assert inspect(connection).get_table_names() == []
    finally:
        reset_engine.dispose()

    previous_database_url = os.environ.get("DATABASE_URL")
    logger_states = {
        name: logger.disabled
        for name, logger in logging.root.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    try:
        os.environ["DATABASE_URL"] = test_database_url
        get_settings.cache_clear()
        command.upgrade(alembic_config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        get_settings.cache_clear()
        for name, disabled in logger_states.items():
            logging.getLogger(name).disabled = disabled

    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def integration_session_factory(
    integration_engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=integration_engine,
        expire_on_commit=False,
    )


def truncate_application_tables(engine: Engine) -> None:
    table_names = [
        table_name
        for table_name in inspect(engine).get_table_names()
        if table_name != "alembic_version"
    ]
    if not table_names:
        return
    quote = engine.dialect.identifier_preparer.quote
    tables = ", ".join(quote(table_name) for table_name in table_names)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def clean_database(integration_engine: Engine) -> Iterator[None]:
    truncate_application_tables(integration_engine)
    try:
        yield
    finally:
        truncate_application_tables(integration_engine)


@pytest.fixture
def db_session(integration_session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = integration_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
