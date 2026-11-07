from datetime import date

import pytest

from src.web.server import _parse_date, build_dashboard_payload


def test_converte_data_iso_do_filtro() -> None:
    assert _parse_date("2026-11-07") == date(2026, 11, 7)
    assert _parse_date(None) is None


def test_rejeita_codigo_fora_do_catalogo_antes_de_consultar_banco() -> None:
    with pytest.raises(ValueError, match="não permitido"):
        build_dashboard_payload(object(), 999, None, None)  # type: ignore[arg-type]


def test_rejeita_intervalo_invertido_antes_de_consultar_banco() -> None:
    with pytest.raises(ValueError, match="data inicial"):
        build_dashboard_payload(  # type: ignore[arg-type]
            object(),
            432,
            date(2026, 11, 7),
            date(2026, 1, 1),
        )
