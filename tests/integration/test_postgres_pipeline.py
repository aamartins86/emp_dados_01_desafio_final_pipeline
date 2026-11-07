"""Integração dos repositórios Bronze, Prata e Ouro com PostgreSQL."""

from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from src.database.gold_repository import (
    reconcile_gold,
    validate_gold_scope,
    validate_silver_contract,
)
from src.database.postgres import initialize_schema
from src.database.repository import persist_artifact_and_log
from src.database.silver_repository import (
    initialize_silver_schema,
    validate_bronze_contract,
)
from src.models import BronzeArtifact, Indicator, IngestionLog


pytestmark = pytest.mark.integration


def test_persiste_artefato_e_log_bronze_na_mesma_execucao(
    postgres_connection: psycopg.Connection,
    temporary_schemas: dict[str, str],
) -> None:
    schema_name = temporary_schemas["bronze"]
    initialize_schema(postgres_connection, schema_name)
    validate_bronze_contract(postgres_connection, schema_name)

    execution_id = uuid4()
    now = datetime.now(timezone.utc)
    indicator = Indicator(name="Meta Selic", slug="selic", code=432)
    parquet_content = b"parquet-de-integracao"
    original_json = [{"data": "01/01/2020", "valor": "4.50"}]
    raw_body = b'[{"data":"01/01/2020","valor":"4.50"}]'
    artifact = BronzeArtifact(
        execution_id=execution_id,
        indicator=indicator,
        filename="selic.parquet",
        parquet_content=parquet_content,
        original_json=original_json,
        raw_body=raw_body,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 1),
        record_count=1,
        file_hash=sha256(parquet_content).hexdigest(),
        ingested_at=now,
    )
    ingestion_log = IngestionLog(
        execution_id=execution_id,
        indicator=indicator,
        endpoint="https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados",
        status_http=200,
        status="SUCESSO",
        record_count=1,
        error_message=None,
        started_at=now,
        finished_at=now,
    )

    persist_artifact_and_log(
        postgres_connection, schema_name, artifact, ingestion_log
    )

    stored = postgres_connection.execute(
        sql.SQL(
            """
            SELECT id_execucao, codigo_sgs, arquivo, json_original,
                   corpo_bruto, quantidade_registros, hash_arquivo
            FROM {}.tb_arquivos_parquet
            """
        ).format(sql.Identifier(schema_name))
    ).fetchone()
    assert stored is not None
    assert stored[0] == execution_id
    assert stored[1] == 432
    assert bytes(stored[2]) == parquet_content
    assert stored[3] == original_json
    assert bytes(stored[4]) == raw_body
    assert stored[5] == 1
    assert stored[6] == sha256(parquet_content).hexdigest()

    log_row = postgres_connection.execute(
        sql.SQL(
            "SELECT status_ingestao, status_http, quantidade_registros "
            "FROM {}.tb_log_ingestao"
        ).format(sql.Identifier(schema_name))
    ).fetchone()
    assert log_row == ("SUCESSO", 200, 1)


def test_reconcilia_prata_e_ouro_com_chaves_e_idempotencia(
    postgres_connection: psycopg.Connection,
    temporary_schemas: dict[str, str],
) -> None:
    silver_schema = temporary_schemas["silver"]
    gold_schema = temporary_schemas["gold"]
    initialize_silver_schema(postgres_connection, silver_schema)
    validate_silver_contract(postgres_connection, silver_schema)

    execution_id = uuid4()
    now = datetime.now(timezone.utc)
    insert_query = sql.SQL(
        """
        INSERT INTO {}.tb_indicadores_economicos (
            id_indicador, codigo_sgs, data_referencia, valor,
            id_execucao_origem, id_arquivo_origem,
            data_ingestao_origem, ordem_registro_origem,
            data_processamento, data_atualizacao
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
    ).format(sql.Identifier(silver_schema))
    rows = [
        (
            1,
            432,
            date(2020, 1, 1),
            Decimal("4.50"),
            execution_id,
            1,
            now,
            1,
            now,
            now,
        ),
        (
            3,
            1,
            date(2020, 1, 2),
            Decimal("4.02"),
            execution_id,
            2,
            now,
            1,
            now,
            now,
        ),
    ]
    with postgres_connection.cursor() as cursor:
        cursor.executemany(insert_query, rows)

    first = reconcile_gold(
        postgres_connection,
        silver_schema,
        gold_schema,
        current_date=date(2020, 1, 3),
    )
    validate_gold_scope(postgres_connection, gold_schema)
    assert first.calendar_rows == 3
    assert first.indicator_rows == 4
    assert first.source_rows == 2
    assert first.inserted == 2

    facts_before = postgres_connection.execute(
        sql.SQL(
            """
            SELECT fato.id_fato, indicador.codigo_sgs, calendario.data,
                   fato.valor_indicador
            FROM {}.fct_indicadores_economicos fato
            JOIN {}.dim_indicador indicador
              ON indicador.id_indicador = fato.id_indicador
            JOIN {}.dim_calendario calendario
              ON calendario.id_data = fato.id_data
            ORDER BY indicador.codigo_sgs
            """
        ).format(
            sql.Identifier(gold_schema),
            sql.Identifier(gold_schema),
            sql.Identifier(gold_schema),
        )
    ).fetchall()
    assert [(row[1], row[2], row[3]) for row in facts_before] == [
        (1, date(2020, 1, 2), Decimal("4.02000000")),
        (432, date(2020, 1, 1), Decimal("4.50000000")),
    ]

    postgres_connection.execute(
        sql.SQL(
            "UPDATE {}.tb_indicadores_economicos "
            "SET valor = 4.75 WHERE codigo_sgs = 432"
        ).format(sql.Identifier(silver_schema))
    )
    postgres_connection.execute(
        sql.SQL(
            "DELETE FROM {}.tb_indicadores_economicos WHERE codigo_sgs = 1"
        ).format(sql.Identifier(silver_schema))
    )

    second = reconcile_gold(
        postgres_connection,
        silver_schema,
        gold_schema,
        current_date=date(2020, 1, 3),
    )
    assert second.updated == 1
    assert second.removed == 1

    facts_after = postgres_connection.execute(
        sql.SQL(
            "SELECT id_fato, valor_indicador "
            "FROM {}.fct_indicadores_economicos"
        ).format(sql.Identifier(gold_schema))
    ).fetchall()
    assert facts_after == [(facts_before[1][0], Decimal("4.75000000"))]

    third = reconcile_gold(
        postgres_connection,
        silver_schema,
        gold_schema,
        current_date=date(2020, 1, 3),
    )
    assert third.inserted == 0
    assert third.updated == 0
    assert third.unchanged == 1
    assert third.removed == 0
