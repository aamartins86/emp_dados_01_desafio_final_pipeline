"""Orquestração da ingestão da camada Bronze."""

from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

from src.config import Settings
from src.database.postgres import connect, ensure_database, initialize_schema
from src.database.repository import persist_artifact_and_log, persist_log
from src.ingestion.bcb_client import (
    BCBIngestionError,
    INDICATORS,
    build_request,
    fetch_indicator,
)
from src.ingestion.parquet import calculate_hash, serialize_records, validate_parquet
from src.models import BronzeArtifact, IngestionLog
from src.utils.logging_config import configure_logging


START_DATE = date(2020, 1, 1)


def _write_local_copy(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def run() -> dict[str, str]:
    settings = Settings.from_env()
    logger = configure_logging(settings.log_dir, settings.log_level)
    execution_id = uuid4()
    end_date = date.today()
    statuses: dict[str, str] = {}

    logger.info("Iniciando execução %s", execution_id)
    try:
        ensure_database(settings)
    except Exception:
        logger.exception("Falha ao validar ou criar o banco PostgreSQL")
        raise

    with connect(settings) as conn:
        initialize_schema(conn, settings.db_schema)

        # Um único cliente, sem retries e sem redirecionamentos automáticos.
        with httpx.Client(timeout=settings.http_timeout_seconds, follow_redirects=False) as client:
            for indicator in INDICATORS:
                started_at = datetime.now(timezone.utc)
                request = build_request(indicator, START_DATE, end_date)
                endpoint = str(request.url)
                status_http = None
                record_count = 0

                try:
                    result = fetch_indicator(client, indicator, START_DATE, end_date)
                    endpoint = result.endpoint
                    status_http = result.status_http
                    record_count = len(result.records)

                    if not result.records:
                        status = "SEM_DADOS"
                        persist_log(
                            conn,
                            settings.db_schema,
                            IngestionLog(
                                execution_id,
                                indicator,
                                endpoint,
                                status_http,
                                status,
                                0,
                                None,
                                started_at,
                                datetime.now(timezone.utc),
                            ),
                        )
                        statuses[indicator.slug] = status
                        logger.warning("%s retornou sem dados", indicator.name)
                        continue

                    parquet_content = serialize_records(result.records)
                    validate_parquet(parquet_content, record_count)
                    filename = f"{indicator.slug}_{execution_id}.parquet"
                    local_path = settings.bronze_path / "banco_central" / indicator.slug / filename
                    _write_local_copy(local_path, parquet_content)

                    finished_at = datetime.now(timezone.utc)
                    artifact = BronzeArtifact(
                        execution_id=execution_id,
                        indicator=indicator,
                        filename=filename,
                        parquet_content=parquet_content,
                        original_json=result.records,
                        raw_body=result.raw_body,
                        start_date=START_DATE,
                        end_date=end_date,
                        record_count=record_count,
                        file_hash=calculate_hash(parquet_content),
                        ingested_at=finished_at,
                    )
                    ingestion_log = IngestionLog(
                        execution_id,
                        indicator,
                        endpoint,
                        status_http,
                        "SUCESSO",
                        record_count,
                        None,
                        started_at,
                        finished_at,
                    )
                    persist_artifact_and_log(
                        conn, settings.db_schema, artifact, ingestion_log
                    )
                    statuses[indicator.slug] = "SUCESSO"
                    logger.info("%s: %s registros persistidos", indicator.name, record_count)
                except Exception as exc:
                    if isinstance(exc, BCBIngestionError):
                        endpoint = exc.endpoint
                        status_http = exc.status_http
                    statuses[indicator.slug] = "FALHA"
                    logger.exception("Falha na ingestão de %s", indicator.name)
                    try:
                        persist_log(
                            conn,
                            settings.db_schema,
                            IngestionLog(
                                execution_id,
                                indicator,
                                endpoint,
                                status_http,
                                "FALHA",
                                record_count,
                                str(exc),
                                started_at,
                                datetime.now(timezone.utc),
                            ),
                        )
                    except Exception:
                        logger.exception("Não foi possível persistir o log da falha")

    logger.info("Execução %s finalizada: %s", execution_id, statuses)
    return statuses


def main() -> int:
    try:
        statuses = run()
    except Exception:
        import logging

        logging.exception("Pipeline Bronze interrompido antes das ingestões")
        return 1
    return 1 if "FALHA" in statuses.values() else 0


if __name__ == "__main__":
    raise SystemExit(main())
