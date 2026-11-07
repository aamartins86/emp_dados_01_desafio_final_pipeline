"""Orquestração da modelagem dimensional Prata para Ouro."""

from datetime import date
import logging

from src.analytics.models import GoldMetrics
from src.config import Settings
from src.database.gold_repository import reconcile_gold
from src.database.postgres import connect, ensure_database
from src.utils.logging_config import configure_logging


def run(processing_date: date | None = None) -> GoldMetrics:
    settings = Settings.from_env()
    logger = configure_logging(
        settings.log_dir,
        settings.log_level,
        logger_name="gold_pipeline",
        filename="gold_pipeline.log",
    )
    logger.info("Iniciando reconciliação Prata -> Ouro")
    ensure_database(settings)

    with connect(settings) as conn:
        metrics = reconcile_gold(
            conn,
            settings.silver_schema,
            settings.gold_schema,
            processing_date or date.today(),
        )

    logger.info(
        "Carga Ouro finalizada: calendário=%s, indicadores=%s, origem=%s, "
        "inseridos=%s, atualizados=%s, inalterados=%s, removidos=%s",
        metrics.calendar_rows,
        metrics.indicator_rows,
        metrics.source_rows,
        metrics.inserted,
        metrics.updated,
        metrics.unchanged,
        metrics.removed,
    )
    return metrics


def main() -> int:
    try:
        run()
    except Exception:
        logging.getLogger("gold_pipeline").exception("Falha na carga da camada Ouro")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
