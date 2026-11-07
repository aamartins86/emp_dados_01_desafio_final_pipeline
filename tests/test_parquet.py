from io import BytesIO

import pyarrow.parquet as pq

from src.ingestion.parquet import calculate_hash, serialize_records, validate_parquet


def test_parquet_preserva_data_e_valor_como_strings() -> None:
    records = [
        {"data": "02/01/2023", "valor": "13.75"},
        {"data": "03/01/2023", "valor": "13,75"},
    ]

    content = serialize_records(records)
    validate_parquet(content, expected_rows=2)
    table = pq.read_table(BytesIO(content))

    assert table.to_pylist() == records
    assert len(calculate_hash(content)) == 64
