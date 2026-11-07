from datetime import date

import httpx

from src.ingestion.bcb_client import INDICATORS, fetch_indicator


def test_lista_exatamente_quatro_indicadores() -> None:
    assert [item.code for item in INDICATORS] == [432, 433, 1, 4389]


def test_fetch_preserva_strings_e_faz_uma_requisicao() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            content=b'[{"data":"02/01/2023","valor":"13.75"}]',
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = fetch_indicator(
            client, INDICATORS[0], date(2023, 1, 1), date(2023, 1, 2)
        )

    assert calls == 1
    assert result.records == [{"data": "02/01/2023", "valor": "13.75"}]
    assert result.raw_body == b'[{"data":"02/01/2023","valor":"13.75"}]'
