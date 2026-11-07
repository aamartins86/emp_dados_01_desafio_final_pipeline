"""Contrato, leitura Bronze e persistência transacional da camada Prata."""

from datetime import datetime
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from src.transformation.deduplication import classify_candidate
from src.transformation.catalog import INDICATOR_CATALOG
from src.transformation.models import (
    BronzeFile,
    RejectedRecord,
    SilverRecord,
    TransformationMetrics,
)


BRONZE_REQUIRED_COLUMNS = {
    "tb_arquivos_parquet": {
        "id_arquivo",
        "id_execucao",
        "indicador",
        "codigo_sgs",
        "arquivo",
        "hash_arquivo",
        "data_ingestao",
    },
    "tb_log_ingestao": {
        "id_execucao",
        "codigo_sgs",
        "status_ingestao",
    },
}


def validate_bronze_contract(conn: psycopg.Connection, bronze_schema: str) -> None:
    rows = conn.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name IN ('tb_arquivos_parquet', 'tb_log_ingestao')
        """,
        (bronze_schema,),
    ).fetchall()
    actual: dict[str, set[str]] = {}
    for table_name, column_name in rows:
        actual.setdefault(table_name, set()).add(column_name)

    problems = []
    for table_name, required in BRONZE_REQUIRED_COLUMNS.items():
        missing = required - actual.get(table_name, set())
        if missing:
            problems.append(f"{table_name}: faltam {sorted(missing)}")
    if problems:
        raise RuntimeError("Contrato Bronze incompatível: " + "; ".join(problems))


def initialize_silver_schema(
    conn: psycopg.Connection,
    silver_schema: str,
) -> None:
    schema = sql.Identifier(silver_schema)
    with conn.transaction():
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(schema))
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.tb_dim_indicador (
                    id_indicador INTEGER PRIMARY KEY,
                    codigo_sgs INTEGER NOT NULL UNIQUE,
                    nome_indicador VARCHAR(150) NOT NULL,
                    unidade_medida VARCHAR(100) NOT NULL,
                    periodicidade VARCHAR(20) NOT NULL,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE
                )
                """
            ).format(schema)
        )
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.tb_indicadores_economicos (
                    id_registro BIGSERIAL PRIMARY KEY,
                    id_indicador INTEGER NOT NULL
                        REFERENCES {}.tb_dim_indicador(id_indicador),
                    codigo_sgs INTEGER NOT NULL,
                    data_referencia DATE NOT NULL,
                    valor NUMERIC(20,8) NOT NULL,
                    id_execucao_origem UUID NOT NULL,
                    id_arquivo_origem BIGINT NOT NULL,
                    data_ingestao_origem TIMESTAMPTZ NOT NULL,
                    ordem_registro_origem INTEGER NOT NULL,
                    data_processamento TIMESTAMPTZ NOT NULL,
                    data_atualizacao TIMESTAMPTZ NOT NULL,
                    CONSTRAINT uq_indicador_data UNIQUE (codigo_sgs, data_referencia)
                )
                """
            ).format(schema, schema)
        )
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.tb_registros_rejeitados (
                    id_rejeicao BIGSERIAL PRIMARY KEY,
                    id_execucao UUID NOT NULL,
                    id_arquivo_origem BIGINT NOT NULL,
                    codigo_sgs INTEGER NOT NULL,
                    dados_originais JSONB NOT NULL,
                    motivo_rejeicao TEXT NOT NULL,
                    data_rejeicao TIMESTAMPTZ NOT NULL
                )
                """
            ).format(schema)
        )
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.tb_log_transformacao (
                    id_log BIGSERIAL PRIMARY KEY,
                    id_execucao UUID NOT NULL UNIQUE,
                    modo_execucao VARCHAR(20) NOT NULL,
                    data_inicio TIMESTAMPTZ NOT NULL,
                    data_fim TIMESTAMPTZ NOT NULL,
                    status VARCHAR(30) NOT NULL
                        CHECK (status IN ('SUCESSO', 'SUCESSO_PARCIAL', 'FALHA')),
                    total_arquivos INTEGER NOT NULL,
                    total_arquivos_falha INTEGER NOT NULL,
                    total_lidos INTEGER NOT NULL,
                    total_validos INTEGER NOT NULL,
                    total_duplicados INTEGER NOT NULL,
                    total_inseridos INTEGER NOT NULL,
                    total_atualizados INTEGER NOT NULL,
                    total_inalterados INTEGER NOT NULL,
                    total_rejeitados INTEGER NOT NULL,
                    mensagem_erro TEXT
                )
                """
            ).format(schema)
        )
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.tb_historico_alteracoes (
                    id_historico BIGSERIAL PRIMARY KEY,
                    codigo_sgs INTEGER NOT NULL,
                    data_referencia DATE NOT NULL,
                    valor_anterior NUMERIC(20,8) NOT NULL,
                    valor_novo NUMERIC(20,8) NOT NULL,
                    id_arquivo_origem BIGINT NOT NULL,
                    id_execucao UUID NOT NULL,
                    data_alteracao TIMESTAMPTZ NOT NULL
                )
                """
            ).format(schema)
        )
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.tb_controle_processamento (
                    id_controle BIGSERIAL PRIMARY KEY,
                    id_arquivo_origem BIGINT NOT NULL,
                    hash_arquivo VARCHAR(64) NOT NULL,
                    id_execucao UUID NOT NULL,
                    data_processamento TIMESTAMPTZ NOT NULL,
                    status_processamento VARCHAR(30) NOT NULL
                        CHECK (status_processamento IN ('SUCESSO', 'FALHA')),
                    mensagem_erro TEXT,
                    CONSTRAINT uq_controle_execucao
                        UNIQUE (id_arquivo_origem, hash_arquivo, id_execucao)
                )
                """
            ).format(schema)
        )

        for indicator in INDICATOR_CATALOG.values():
            conn.execute(
                sql.SQL(
                    """
                    INSERT INTO {}.tb_dim_indicador (
                        id_indicador, codigo_sgs, nome_indicador,
                        unidade_medida, periodicidade, ativo
                    ) VALUES (%s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (codigo_sgs) DO UPDATE SET
                        nome_indicador = EXCLUDED.nome_indicador,
                        unidade_medida = EXCLUDED.unidade_medida,
                        periodicidade = EXCLUDED.periodicidade,
                        ativo = TRUE
                    """
                ).format(schema),
                (
                    indicator.indicator_id,
                    indicator.sgs_code,
                    indicator.name,
                    indicator.unit,
                    indicator.periodicity,
                ),
            )


def fetch_bronze_files(
    conn: psycopg.Connection,
    bronze_schema: str,
    silver_schema: str,
    full_reprocess: bool,
) -> list[BronzeFile]:
    incremental_filter = sql.SQL("")
    if not full_reprocess:
        incremental_filter = sql.SQL(
            """
            AND NOT EXISTS (
                SELECT 1
                FROM {}.tb_controle_processamento controle
                WHERE controle.id_arquivo_origem = arquivo.id_arquivo
                  AND controle.hash_arquivo = arquivo.hash_arquivo
                  AND controle.status_processamento = 'SUCESSO'
            )
            """
        ).format(sql.Identifier(silver_schema))

    query = sql.SQL(
        """
        SELECT
            arquivo.id_arquivo,
            arquivo.id_execucao,
            arquivo.indicador,
            arquivo.codigo_sgs,
            arquivo.arquivo,
            arquivo.hash_arquivo,
            arquivo.data_ingestao
        FROM {}.tb_arquivos_parquet arquivo
        WHERE EXISTS (
            SELECT 1
            FROM {}.tb_log_ingestao log
            WHERE log.id_execucao = arquivo.id_execucao
              AND log.codigo_sgs = arquivo.codigo_sgs
              AND log.status_ingestao = 'SUCESSO'
        )
        {}
        ORDER BY arquivo.data_ingestao, arquivo.id_arquivo
        """
    ).format(
        sql.Identifier(bronze_schema),
        sql.Identifier(bronze_schema),
        incremental_filter,
    )
    rows = conn.execute(query).fetchall()
    return [
        BronzeFile(
            file_id=row[0],
            origin_execution_id=row[1],
            indicator_name=row[2],
            sgs_code=row[3],
            content=bytes(row[4]),
            file_hash=row[5],
            ingested_at=row[6],
        )
        for row in rows
    ]


def _insert_log(
    conn: psycopg.Connection,
    silver_schema: str,
    execution_id: UUID,
    mode: str,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    metrics: TransformationMetrics,
    error_message: str | None,
) -> None:
    conn.execute(
        sql.SQL(
            """
            INSERT INTO {}.tb_log_transformacao (
                id_execucao, modo_execucao, data_inicio, data_fim, status,
                total_arquivos, total_arquivos_falha, total_lidos,
                total_validos, total_duplicados, total_inseridos,
                total_atualizados, total_inalterados, total_rejeitados,
                mensagem_erro
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        ).format(sql.Identifier(silver_schema)),
        (
            execution_id,
            mode,
            started_at,
            finished_at,
            status,
            metrics.total_files,
            metrics.total_failed_files,
            metrics.total_read,
            metrics.total_valid,
            metrics.total_duplicates,
            metrics.total_inserted,
            metrics.total_updated,
            metrics.total_unchanged,
            metrics.total_rejected,
            error_message,
        ),
    )


def persist_transformation(
    conn: psycopg.Connection,
    silver_schema: str,
    execution_id: UUID,
    mode: str,
    started_at: datetime,
    finished_at: datetime,
    winners: list[SilverRecord],
    rejected: list[RejectedRecord],
    successful_files: list[BronzeFile],
    failed_files: list[tuple[BronzeFile, str]],
    metrics: TransformationMetrics,
) -> None:
    schema = sql.Identifier(silver_schema)
    with conn.transaction():
        for item in rejected:
            conn.execute(
                sql.SQL(
                    """
                    INSERT INTO {}.tb_registros_rejeitados (
                        id_execucao, id_arquivo_origem, codigo_sgs,
                        dados_originais, motivo_rejeicao, data_rejeicao
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """
                ).format(schema),
                (
                    execution_id,
                    item.origin_file_id,
                    item.sgs_code,
                    Jsonb(item.original_data),
                    item.reason,
                    finished_at,
                ),
            )

        for record in winners:
            current = conn.execute(
                sql.SQL(
                    """
                    SELECT valor, data_ingestao_origem, id_arquivo_origem,
                           ordem_registro_origem
                    FROM {}.tb_indicadores_economicos
                    WHERE codigo_sgs = %s AND data_referencia = %s
                    FOR UPDATE
                    """
                ).format(schema),
                (record.sgs_code, record.reference_date),
            ).fetchone()

            if current is None:
                conn.execute(
                    sql.SQL(
                        """
                        INSERT INTO {}.tb_indicadores_economicos (
                            id_indicador, codigo_sgs, data_referencia, valor,
                            id_execucao_origem, id_arquivo_origem,
                            data_ingestao_origem, ordem_registro_origem,
                            data_processamento, data_atualizacao
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                    ).format(schema),
                    (
                        record.indicator_id,
                        record.sgs_code,
                        record.reference_date,
                        record.value,
                        record.origin_execution_id,
                        record.origin_file_id,
                        record.origin_ingested_at,
                        record.origin_row_number,
                        finished_at,
                        finished_at,
                    ),
                )
                metrics.total_inserted += 1
                continue

            current_value = current[0]
            current_precedence = (current[1], current[2], current[3])
            candidate_action = classify_candidate(
                current_value, current_precedence, record
            )
            if candidate_action != "UPDATE":
                metrics.total_unchanged += 1
                continue

            conn.execute(
                sql.SQL(
                    """
                    INSERT INTO {}.tb_historico_alteracoes (
                        codigo_sgs, data_referencia, valor_anterior, valor_novo,
                        id_arquivo_origem, id_execucao, data_alteracao
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                ).format(schema),
                (
                    record.sgs_code,
                    record.reference_date,
                    current_value,
                    record.value,
                    record.origin_file_id,
                    execution_id,
                    finished_at,
                ),
            )
            conn.execute(
                sql.SQL(
                    """
                    UPDATE {}.tb_indicadores_economicos
                    SET id_indicador = %s,
                        valor = %s,
                        id_execucao_origem = %s,
                        id_arquivo_origem = %s,
                        data_ingestao_origem = %s,
                        ordem_registro_origem = %s,
                        data_processamento = %s,
                        data_atualizacao = %s
                    WHERE codigo_sgs = %s AND data_referencia = %s
                    """
                ).format(schema),
                (
                    record.indicator_id,
                    record.value,
                    record.origin_execution_id,
                    record.origin_file_id,
                    record.origin_ingested_at,
                    record.origin_row_number,
                    finished_at,
                    finished_at,
                    record.sgs_code,
                    record.reference_date,
                ),
            )
            metrics.total_updated += 1

        for bronze_file in successful_files:
            conn.execute(
                sql.SQL(
                    """
                    INSERT INTO {}.tb_controle_processamento (
                        id_arquivo_origem, hash_arquivo, id_execucao,
                        data_processamento, status_processamento, mensagem_erro
                    ) VALUES (%s, %s, %s, %s, 'SUCESSO', NULL)
                    """
                ).format(schema),
                (
                    bronze_file.file_id,
                    bronze_file.file_hash,
                    execution_id,
                    finished_at,
                ),
            )

        for bronze_file, error_message in failed_files:
            conn.execute(
                sql.SQL(
                    """
                    INSERT INTO {}.tb_controle_processamento (
                        id_arquivo_origem, hash_arquivo, id_execucao,
                        data_processamento, status_processamento, mensagem_erro
                    ) VALUES (%s, %s, %s, %s, 'FALHA', %s)
                    """
                ).format(schema),
                (
                    bronze_file.file_id,
                    bronze_file.file_hash,
                    execution_id,
                    finished_at,
                    error_message,
                ),
            )

        status = "SUCESSO_PARCIAL" if failed_files else "SUCESSO"
        _insert_log(
            conn,
            silver_schema,
            execution_id,
            mode,
            started_at,
            finished_at,
            status,
            metrics,
            None,
        )


def persist_failure_log(
    conn: psycopg.Connection,
    silver_schema: str,
    execution_id: UUID,
    mode: str,
    started_at: datetime,
    finished_at: datetime,
    metrics: TransformationMetrics,
    error_message: str,
) -> None:
    with conn.transaction():
        _insert_log(
            conn,
            silver_schema,
            execution_id,
            mode,
            started_at,
            finished_at,
            "FALHA",
            metrics,
            error_message,
        )
