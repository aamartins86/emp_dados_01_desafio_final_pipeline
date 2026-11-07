"""Modelos usados no processamento da camada Prata."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class BronzeFile:
    file_id: int
    origin_execution_id: UUID
    indicator_name: str
    sgs_code: int
    content: bytes
    file_hash: str
    ingested_at: datetime


@dataclass(frozen=True)
class SilverRecord:
    indicator_id: int
    sgs_code: int
    reference_date: date
    value: Decimal
    origin_execution_id: UUID
    origin_file_id: int
    origin_ingested_at: datetime
    origin_row_number: int

    @property
    def natural_key(self) -> tuple[int, date]:
        return (self.sgs_code, self.reference_date)

    @property
    def precedence(self) -> tuple[datetime, int, int]:
        return (
            self.origin_ingested_at,
            self.origin_file_id,
            self.origin_row_number,
        )


@dataclass(frozen=True)
class RejectedRecord:
    origin_file_id: int
    sgs_code: int
    original_data: dict[str, object]
    reason: str


@dataclass
class TransformationMetrics:
    total_read: int = 0
    total_valid: int = 0
    total_duplicates: int = 0
    total_inserted: int = 0
    total_updated: int = 0
    total_unchanged: int = 0
    total_rejected: int = 0
    total_files: int = 0
    total_failed_files: int = 0
