"""Fixtures para testes de integração em um PostgreSQL real."""

import os
from collections.abc import Iterator
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from src.config import Settings


@pytest.fixture
def postgres_connection() -> Iterator[psycopg.Connection]:
    """Conecta ao banco exclusivo do CI ou, sob solicitação, ao banco local."""
    dsn = os.getenv("POSTGRES_TEST_DSN", "").strip()
    if dsn:
        conn = psycopg.connect(dsn, autocommit=True)
    elif os.getenv("RUN_POSTGRES_INTEGRATION") == "1":
        settings = Settings.from_env()
        conn = psycopg.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            autocommit=True,
        )
    else:
        pytest.skip(
            "Defina POSTGRES_TEST_DSN ou RUN_POSTGRES_INTEGRATION=1 "
            "para executar os testes PostgreSQL."
        )

    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def temporary_schemas(
    postgres_connection: psycopg.Connection,
) -> Iterator[dict[str, str]]:
    """Fornece schemas únicos e garante sua remoção mesmo após uma falha."""
    suffix = uuid4().hex[:12]
    schemas = {
        "bronze": f"it_bronze_{suffix}",
        "silver": f"it_prata_{suffix}",
        "gold": f"it_ouro_{suffix}",
    }
    try:
        yield schemas
    finally:
        for schema_name in reversed(tuple(schemas.values())):
            postgres_connection.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema_name)
                )
            )
