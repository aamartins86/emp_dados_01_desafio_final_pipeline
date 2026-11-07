from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from src.transformation.deduplication import classify_candidate, select_winners
from src.transformation.models import SilverRecord


def make_record(value: str, file_id: int, hour: int) -> SilverRecord:
    return SilverRecord(
        indicator_id=1,
        sgs_code=432,
        reference_date=date(2023, 1, 2),
        value=Decimal(value),
        origin_execution_id=uuid4(),
        origin_file_id=file_id,
        origin_ingested_at=datetime(2026, 11, 7, hour, tzinfo=timezone.utc),
        origin_row_number=1,
    )


def test_deduplica_e_escolhe_ingestao_mais_recente() -> None:
    older = make_record("13.75000000", file_id=1, hour=10)
    newer = make_record("13.50000000", file_id=2, hour=11)

    winners, duplicates = select_winners([newer, older])

    assert duplicates == 1
    assert winners == [newer]


def test_resultado_independe_da_ordem_de_entrada() -> None:
    older = make_record("13.75000000", file_id=1, hour=10)
    newer = make_record("13.50000000", file_id=2, hour=11)

    first, _ = select_winners([older, newer])
    second, _ = select_winners([newer, older])

    assert first == second == [newer]


def test_atualiza_somente_valor_divergente_com_precedencia_mais_recente() -> None:
    older = make_record("13.75000000", file_id=1, hour=10)
    newer = make_record("13.50000000", file_id=2, hour=11)

    assert classify_candidate(
        older.value, older.precedence, newer
    ) == "UPDATE"
    assert classify_candidate(
        newer.value, newer.precedence, older
    ) == "STALE"
    assert classify_candidate(
        newer.value, older.precedence, newer
    ) == "UNCHANGED"
