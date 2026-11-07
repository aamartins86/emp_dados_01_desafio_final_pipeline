"""Leitura, validação e normalização dos registros Bronze."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import re

import pyarrow.parquet as pq

from src.transformation.catalog import INDICATOR_CATALOG
from src.transformation.models import BronzeFile, RejectedRecord, SilverRecord


PROJECT_START_DATE = date(2023, 1, 1)
DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")
VALUE_PATTERN = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
SCALE = Decimal("0.00000001")
NUMERIC_LIMIT = Decimal("1000000000000")


class FileIntegrityError(ValueError):
    """Indica que um arquivo Bronze não pode ser processado com segurança."""


def _reject(
    bronze_file: BronzeFile,
    raw_record: object,
    reason: str,
) -> RejectedRecord:
    original = raw_record if isinstance(raw_record, dict) else {"registro": raw_record}
    return RejectedRecord(
        origin_file_id=bronze_file.file_id,
        sgs_code=bronze_file.sgs_code,
        original_data=original,
        reason=reason,
    )


def _parse_date(raw_value: object, processing_date: date) -> date:
    if not isinstance(raw_value, str) or not DATE_PATTERN.fullmatch(raw_value):
        raise ValueError("data ausente ou fora do formato DD/MM/YYYY")
    try:
        parsed = datetime.strptime(raw_value, "%d/%m/%Y").date()
    except ValueError as exc:
        raise ValueError("data inválida") from exc
    if parsed < PROJECT_START_DATE or parsed > processing_date:
        raise ValueError("data fora do intervalo configurado para o projeto")
    return parsed


def _parse_value(raw_value: object) -> Decimal:
    if not isinstance(raw_value, str) or not VALUE_PATTERN.fullmatch(raw_value):
        raise ValueError("valor ausente ou não numérico")
    try:
        parsed = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ValueError("valor inválido") from exc
    if not parsed.is_finite():
        raise ValueError("valor não finito")
    quantized = parsed.quantize(SCALE)
    if quantized != parsed:
        raise ValueError("valor possui mais de oito casas decimais")
    if abs(quantized) >= NUMERIC_LIMIT:
        raise ValueError("valor excede NUMERIC(20,8)")
    return quantized


def normalize_file(
    bronze_file: BronzeFile,
    processing_date: date | None = None,
) -> tuple[list[SilverRecord], list[RejectedRecord], int]:
    """Normaliza um Parquet Bronze, preservando a rastreabilidade por linha."""
    calculated_hash = sha256(bronze_file.content).hexdigest()
    if calculated_hash != bronze_file.file_hash:
        raise FileIntegrityError("hash SHA-256 do Parquet não confere")

    try:
        table = pq.read_table(BytesIO(bronze_file.content))
    except Exception as exc:
        raise FileIntegrityError(f"Parquet inválido ou ilegível: {exc}") from exc

    required_columns = {"data", "valor"}
    if not required_columns.issubset(table.column_names):
        raise FileIntegrityError("Parquet não contém as colunas data e valor")

    indicator = INDICATOR_CATALOG.get(bronze_file.sgs_code)
    rows = table.select(["data", "valor"]).to_pylist()
    normalized: list[SilverRecord] = []
    rejected: list[RejectedRecord] = []
    current_date = processing_date or date.today()

    for row_number, raw_record in enumerate(rows, start=1):
        if indicator is None:
            rejected.append(_reject(bronze_file, raw_record, "código SGS não cadastrado"))
            continue
        try:
            reference_date = _parse_date(raw_record.get("data"), current_date)
            value = _parse_value(raw_record.get("valor"))
        except ValueError as exc:
            rejected.append(_reject(bronze_file, raw_record, str(exc)))
            continue

        normalized.append(
            SilverRecord(
                indicator_id=indicator.indicator_id,
                sgs_code=indicator.sgs_code,
                reference_date=reference_date,
                value=value,
                origin_execution_id=bronze_file.origin_execution_id,
                origin_file_id=bronze_file.file_id,
                origin_ingested_at=bronze_file.ingested_at,
                origin_row_number=row_number,
            )
        )

    return normalized, rejected, len(rows)
