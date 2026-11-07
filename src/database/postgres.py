"""Criação e conexão segura com o PostgreSQL local."""

import psycopg
from psycopg import sql

from src.config import Settings


def _connection_kwargs(settings: Settings, dbname: str) -> dict[str, object]:
    return {
        "host": settings.db_host,
        "port": settings.db_port,
        "dbname": dbname,
        "user": settings.db_user,
        "password": settings.db_password,
    }


def ensure_database(settings: Settings) -> None:
    """Cria o database de destino quando ele ainda não existe."""
    with psycopg.connect(**_connection_kwargs(settings, "postgres"), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (settings.db_name,)
        ).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(settings.db_name)))


def connect(settings: Settings) -> psycopg.Connection:
    return psycopg.connect(**_connection_kwargs(settings, settings.db_name))


def initialize_schema(conn: psycopg.Connection, schema_name: str) -> None:
    schema = sql.Identifier(schema_name)
    with conn.transaction():
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(schema))
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.tb_arquivos_parquet (
                    id_arquivo BIGSERIAL PRIMARY KEY,
                    id_execucao UUID NOT NULL,
                    indicador VARCHAR(100) NOT NULL,
                    codigo_sgs INTEGER NOT NULL,
                    nome_arquivo VARCHAR(255) NOT NULL,
                    arquivo BYTEA NOT NULL,
                    json_original JSONB NOT NULL,
                    corpo_bruto BYTEA NOT NULL,
                    data_inicio DATE NOT NULL,
                    data_fim DATE NOT NULL,
                    quantidade_registros INTEGER NOT NULL,
                    hash_arquivo VARCHAR(64) NOT NULL,
                    data_ingestao TIMESTAMPTZ NOT NULL
                )
                """
            ).format(schema)
        )
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.tb_log_ingestao (
                    id_log BIGSERIAL PRIMARY KEY,
                    id_execucao UUID NOT NULL,
                    indicador VARCHAR(100) NOT NULL,
                    codigo_sgs INTEGER NOT NULL,
                    endpoint TEXT NOT NULL,
                    status_http INTEGER,
                    status_ingestao VARCHAR(30) NOT NULL
                        CHECK (status_ingestao IN ('SUCESSO', 'FALHA', 'SEM_DADOS')),
                    quantidade_registros INTEGER NOT NULL,
                    mensagem_erro TEXT,
                    data_inicio_execucao TIMESTAMPTZ NOT NULL,
                    data_fim_execucao TIMESTAMPTZ NOT NULL
                )
                """
            ).format(schema)
        )
