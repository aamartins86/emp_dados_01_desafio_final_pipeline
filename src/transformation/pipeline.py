"""Orquestração da transformação Bronze para Prata."""

import argparse
from datetime import date, datetime, timezone
from uuid import uuid4

from src.config import Settings
from src.database.postgres import connect, ensure_database
from src.database.silver_repository import (
    fetch_bronze_files,
    initialize_silver_schema,
    persist_failure_log,
    persist_transformation,
    validate_bronze_contract,
)
from src.transformation.deduplication import select_winners
from src.transformation.models import TransformationMetrics
from src.transformation.normalizer import FileIntegrityError, normalize_file
from src.utils.logging_config import configure_logging


def run(full_reprocess: bool = False) -> TransformationMetrics:
    settings = Settings.from_env()
    logger = configure_logging(
        settings.log_dir,
        settings.log_level,
        logger_name="silver_pipeline",
        filename="silver_pipeline.log",
    )
    execution_id = uuid4()
    started_at = datetime.now(timezone.utc)
    mode = "COMPLETO" if full_reprocess else "INCREMENTAL"
    metrics = TransformationMetrics()

    logger.info("Iniciando transformação %s no modo %s", execution_id, mode)
    ensure_database(settings)

    with connect(settings) as conn:
        initialize_silver_schema(conn, settings.silver_schema)
        validate_bronze_contract(conn, settings.db_schema)
        bronze_files = fetch_bronze_files(
            conn,
            settings.db_schema,
            settings.silver_schema,
            full_reprocess,
        )
        conn.commit()

        metrics.total_files = len(bronze_files)
        valid_records = []
        rejected_records = []
        successful_files = []
        failed_files = []

        for bronze_file in bronze_files:
            try:
                normalized, rejected, total_rows = normalize_file(
                    bronze_file,
                    processing_date=date.today(),
                )
                metrics.total_read += total_rows
                metrics.total_valid += len(normalized)
                metrics.total_rejected += len(rejected)
                valid_records.extend(normalized)
                rejected_records.extend(rejected)
                successful_files.append(bronze_file)
            except FileIntegrityError as exc:
                metrics.total_failed_files += 1
                failed_files.append((bronze_file, str(exc)))
                logger.error(
                    "Arquivo Bronze %s bloqueado por integridade: %s",
                    bronze_file.file_id,
                    exc,
                )

        winners, duplicate_count = select_winners(valid_records)
        metrics.total_duplicates = duplicate_count
        finished_at = datetime.now(timezone.utc)

        try:
            persist_transformation(
                conn=conn,
                silver_schema=settings.silver_schema,
                execution_id=execution_id,
                mode=mode,
                started_at=started_at,
                finished_at=finished_at,
                winners=winners,
                rejected=rejected_records,
                successful_files=successful_files,
                failed_files=failed_files,
                metrics=metrics,
            )
        except Exception as exc:
            conn.rollback()
            logger.exception("Falha na persistência da transformação %s", execution_id)
            try:
                persist_failure_log(
                    conn,
                    settings.silver_schema,
                    execution_id,
                    mode,
                    started_at,
                    datetime.now(timezone.utc),
                    metrics,
                    str(exc),
                )
            except Exception:
                logger.exception("Não foi possível persistir o log da falha")
            raise

    logger.info(
        "Transformação %s finalizada: arquivos=%s, lidos=%s, válidos=%s, "
        "duplicados=%s, inseridos=%s, atualizados=%s, inalterados=%s, "
        "rejeitados=%s, arquivos_falha=%s",
        execution_id,
        metrics.total_files,
        metrics.total_read,
        metrics.total_valid,
        metrics.total_duplicates,
        metrics.total_inserted,
        metrics.total_updated,
        metrics.total_unchanged,
        metrics.total_rejected,
        metrics.total_failed_files,
    )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transforma os arquivos Bronze na camada Prata."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Reprocessa todos os arquivos Bronze válidos.",
    )
    args = parser.parse_args()

    try:
        metrics = run(full_reprocess=args.full)
    except Exception:
        return 1
    return 1 if metrics.total_failed_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
