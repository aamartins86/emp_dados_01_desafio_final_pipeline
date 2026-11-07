"""Deduplicação determinística pela chave natural da camada Prata."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from src.transformation.models import SilverRecord


def select_winners(
    records: list[SilverRecord],
) -> tuple[list[SilverRecord], int]:
    winners: dict[tuple[int, object], SilverRecord] = {}
    duplicates = 0

    for record in records:
        current = winners.get(record.natural_key)
        if current is None:
            winners[record.natural_key] = record
            continue
        duplicates += 1
        if record.precedence > current.precedence:
            winners[record.natural_key] = record

    ordered = sorted(
        winners.values(), key=lambda item: (item.sgs_code, item.reference_date)
    )
    return ordered, duplicates


def classify_candidate(
    current_value: Decimal,
    current_precedence: tuple[datetime, int, int],
    candidate: SilverRecord,
) -> Literal["UNCHANGED", "UPDATE", "STALE"]:
    if current_value == candidate.value:
        return "UNCHANGED"
    if candidate.precedence > current_precedence:
        return "UPDATE"
    return "STALE"
