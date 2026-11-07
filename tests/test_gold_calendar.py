from datetime import date

import pytest

from src.analytics.calendar import build_calendar


def test_calendario_e_continuo_e_inclusivo() -> None:
    rows = build_calendar(date(2023, 1, 1), date(2023, 1, 3))

    assert [row.value for row in rows] == [
        date(2023, 1, 1),
        date(2023, 1, 2),
        date(2023, 1, 3),
    ]


def test_atributos_do_calendario_em_portugues() -> None:
    row = build_calendar(date(2026, 11, 7), date(2026, 11, 7))[0]

    assert row.as_tuple() == (
        20261107,
        date(2026, 11, 7),
        7,
        11,
        "Novembro",
        4,
        2026,
        202611,
        "Nov/2026",
        6,
        "Sábado",
        True,
    )


def test_calendario_rejeita_intervalo_invertido() -> None:
    with pytest.raises(ValueError, match="anterior"):
        build_calendar(date(2023, 1, 2), date(2023, 1, 1))
