"""Cliente sem retentativas para a API SGS do Banco Central."""

from datetime import date
import json

import httpx

from src.models import FetchResult, Indicator


BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

INDICATORS = (
    Indicator("Meta Selic", "selic", 432),
    Indicator("IPCA", "ipca", 433),
    Indicator("Taxa de câmbio - Livre - Dólar americano (venda) - diário", "dolar", 1),
    Indicator("CDI anualizado", "cdi", 4389),
)


class BCBIngestionError(RuntimeError):
    def __init__(self, message: str, endpoint: str, status_http: int | None = None):
        super().__init__(message)
        self.endpoint = endpoint
        self.status_http = status_http


def build_request(indicator: Indicator, start_date: date, end_date: date) -> httpx.Request:
    return httpx.Request(
        "GET",
        BASE_URL.format(code=indicator.code),
        params={
            "formato": "json",
            "dataInicial": start_date.strftime("%d/%m/%Y"),
            "dataFinal": end_date.strftime("%d/%m/%Y"),
        },
    )


def _validate_records(payload: object, endpoint: str, status_http: int) -> list[dict[str, str]]:
    if not isinstance(payload, list):
        raise BCBIngestionError("A resposta JSON não é uma lista", endpoint, status_http)

    for position, record in enumerate(payload):
        if not isinstance(record, dict):
            raise BCBIngestionError(
                f"Registro {position} não é um objeto JSON", endpoint, status_http
            )
        if "data" not in record or "valor" not in record:
            raise BCBIngestionError(
                f"Registro {position} não contém os campos data e valor", endpoint, status_http
            )
        if not isinstance(record["data"], str) or not isinstance(record["valor"], str):
            raise BCBIngestionError(
                f"Registro {position} não preserva data e valor como strings",
                endpoint,
                status_http,
            )

    return payload


def fetch_indicator(
    client: httpx.Client,
    indicator: Indicator,
    start_date: date,
    end_date: date,
) -> FetchResult:
    """Executa exatamente uma tentativa HTTP para um indicador."""
    request = build_request(indicator, start_date, end_date)
    endpoint = str(request.url)
    try:
        response = client.send(request)
    except httpx.HTTPError as exc:
        raise BCBIngestionError(f"Falha de comunicação com o BCB: {exc}", endpoint) from exc

    raw_body = response.content
    if response.status_code != 200:
        raise BCBIngestionError(
            f"BCB retornou HTTP {response.status_code}", endpoint, response.status_code
        )
    if not raw_body:
        return FetchResult([], raw_body, endpoint, response.status_code)

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BCBIngestionError(
            "Resposta do BCB incompatível com JSON", endpoint, response.status_code
        ) from exc

    records = _validate_records(payload, endpoint, response.status_code)
    return FetchResult(records, raw_body, endpoint, response.status_code)
