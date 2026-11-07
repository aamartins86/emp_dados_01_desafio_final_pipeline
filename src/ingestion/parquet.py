"""Serialização e validação dos arquivos Parquet da camada Bronze."""

from hashlib import sha256
from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq


BRONZE_SCHEMA = pa.schema(
    [
        pa.field("data", pa.string(), nullable=True),
        pa.field("valor", pa.string(), nullable=True),
    ]
)


def serialize_records(records: list[dict[str, str]]) -> bytes:
    table = pa.Table.from_arrays(
        [
            pa.array([record["data"] for record in records], type=pa.string()),
            pa.array([record["valor"] for record in records], type=pa.string()),
        ],
        schema=BRONZE_SCHEMA,
    )
    buffer = BytesIO()
    pq.write_table(table, buffer, compression="snappy")
    return buffer.getvalue()


def validate_parquet(content: bytes, expected_rows: int) -> None:
    table = pq.read_table(BytesIO(content))
    if table.schema != BRONZE_SCHEMA:
        raise ValueError(f"Schema Parquet inesperado: {table.schema}")
    if table.num_rows != expected_rows:
        raise ValueError(
            f"Parquet contém {table.num_rows} linhas; esperado: {expected_rows}"
        )


def calculate_hash(content: bytes) -> str:
    return sha256(content).hexdigest()
