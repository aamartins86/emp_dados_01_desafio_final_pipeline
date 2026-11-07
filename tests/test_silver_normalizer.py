from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest

from src.ingestion.parquet import serialize_records
from src.transformation.models import BronzeFile
from src.transformation.normalizer import FileIntegrityError, normalize_file


def make_bronze_file(records: list[dict[str, str]], sgs_code: int = 432) -> BronzeFile:
    content = serialize_records(records)
    return BronzeFile(
        file_id=10,
        origin_execution_id=uuid4(),
        indicator_name="Indicador de teste",
        sgs_code=sgs_code,
        content=content,
        file_hash=sha256(content).hexdigest(),
        ingested_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )


def test_normaliza_data_e_valor_sem_perder_precisao() -> None:
    bronze_file = make_bronze_file(
        [{"data": "02/01/2023", "valor": "-13.75000000"}]
    )

    normalized, rejected, total = normalize_file(
        bronze_file, processing_date=date(2026, 11, 7)
    )

    assert total == 1
    assert rejected == []
    assert normalized[0].reference_date == date(2023, 1, 2)
    assert normalized[0].value == Decimal("-13.75000000")
    assert normalized[0].origin_row_number == 1


def test_aceita_data_desde_o_inicio_de_2020() -> None:
    bronze_file = make_bronze_file([{"data": "01/01/2020", "valor": "4.50"}])

    normalized, rejected, total = normalize_file(
        bronze_file, processing_date=date(2026, 11, 7)
    )

    assert total == 1
    assert rejected == []
    assert normalized[0].reference_date == date(2020, 1, 1)


def test_rejeita_data_e_valor_invalidos_sem_substituir_por_zero() -> None:
    bronze_file = make_bronze_file(
        [
            {"data": "31/02/2023", "valor": "13.75"},
            {"data": "02/01/2023", "valor": "texto"},
        ]
    )

    normalized, rejected, total = normalize_file(
        bronze_file, processing_date=date(2026, 11, 7)
    )

    assert total == 2
    assert normalized == []
    assert len(rejected) == 2
    assert "data inválida" in rejected[0].reason
    assert "não numérico" in rejected[1].reason


def test_bloqueia_parquet_com_hash_divergente() -> None:
    bronze_file = make_bronze_file([{"data": "02/01/2023", "valor": "13.75"}])
    invalid_file = BronzeFile(
        **{**bronze_file.__dict__, "file_hash": "0" * 64}
    )

    with pytest.raises(FileIntegrityError, match="SHA-256"):
        normalize_file(invalid_file, processing_date=date(2026, 11, 7))
