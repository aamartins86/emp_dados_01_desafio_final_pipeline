"""Modelos compartilhados entre ingestão e persistência."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True)
class Indicator:
    name: str
    slug: str
    code: int


@dataclass(frozen=True)
class FetchResult:
    records: list[dict[str, str]]
    raw_body: bytes
    endpoint: str
    status_http: int


@dataclass(frozen=True)
class BronzeArtifact:
    execution_id: UUID
    indicator: Indicator
    filename: str
    parquet_content: bytes
    original_json: list[dict[str, str]]
    raw_body: bytes
    start_date: date
    end_date: date
    record_count: int
    file_hash: str
    ingested_at: datetime


@dataclass(frozen=True)
class IngestionLog:
    execution_id: UUID
    indicator: Indicator
    endpoint: str
    status_http: int | None
    status: str
    record_count: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime
