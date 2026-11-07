"""Modelos usados na carga dimensional da camada Ouro."""

from dataclasses import dataclass
from datetime import date


MONTH_NAMES = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)

WEEKDAY_NAMES = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)


@dataclass(frozen=True)
class CalendarDay:
    """Uma linha determinística da dimensão calendário."""

    value: date

    @property
    def id_date(self) -> int:
        return self.value.year * 10_000 + self.value.month * 100 + self.value.day

    @property
    def quarter(self) -> int:
        return (self.value.month - 1) // 3 + 1

    def as_tuple(self) -> tuple[object, ...]:
        month_name = MONTH_NAMES[self.value.month - 1]
        return (
            self.id_date,
            self.value,
            self.value.day,
            self.value.month,
            month_name,
            self.quarter,
            self.value.year,
            self.value.year * 100 + self.value.month,
            f"{month_name[:3]}/{self.value.year}",
            self.value.isoweekday(),
            WEEKDAY_NAMES[self.value.weekday()],
            self.value.weekday() >= 5,
        )


@dataclass
class GoldMetrics:
    calendar_rows: int = 0
    indicator_rows: int = 0
    source_rows: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
