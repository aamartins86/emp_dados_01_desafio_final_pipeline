"""Persistência transacional dos artefatos e logs Bronze."""

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from src.models import BronzeArtifact, IngestionLog


def _insert_log(
    conn: psycopg.Connection, schema_name: str, ingestion_log: IngestionLog
) -> None:
    conn.execute(
        sql.SQL(
            """
            INSERT INTO {}.tb_log_ingestao (
                id_execucao, indicador, codigo_sgs, endpoint, status_http,
                status_ingestao, quantidade_registros, mensagem_erro,
                data_inicio_execucao, data_fim_execucao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        ).format(sql.Identifier(schema_name)),
        (
            ingestion_log.execution_id,
            ingestion_log.indicator.name,
            ingestion_log.indicator.code,
            ingestion_log.endpoint,
            ingestion_log.status_http,
            ingestion_log.status,
            ingestion_log.record_count,
            ingestion_log.error_message,
            ingestion_log.started_at,
            ingestion_log.finished_at,
        ),
    )


def persist_artifact_and_log(
    conn: psycopg.Connection,
    schema_name: str,
    artifact: BronzeArtifact,
    ingestion_log: IngestionLog,
) -> None:
    with conn.transaction():
        conn.execute(
            sql.SQL(
                """
                INSERT INTO {}.tb_arquivos_parquet (
                    id_execucao, indicador, codigo_sgs, nome_arquivo, arquivo,
                    json_original, corpo_bruto, data_inicio, data_fim,
                    quantidade_registros, hash_arquivo, data_ingestao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            ).format(sql.Identifier(schema_name)),
            (
                artifact.execution_id,
                artifact.indicator.name,
                artifact.indicator.code,
                artifact.filename,
                artifact.parquet_content,
                Jsonb(artifact.original_json),
                artifact.raw_body,
                artifact.start_date,
                artifact.end_date,
                artifact.record_count,
                artifact.file_hash,
                artifact.ingested_at,
            ),
        )
        _insert_log(conn, schema_name, ingestion_log)


def persist_log(
    conn: psycopg.Connection, schema_name: str, ingestion_log: IngestionLog
) -> None:
    with conn.transaction():
        _insert_log(conn, schema_name, ingestion_log)
