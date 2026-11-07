"""Geração determinística da dimensão calendário."""

from datetime import date, timedelta

from src.analytics.models import CalendarDay


CALENDAR_START = date(2020, 1, 1)


def build_calendar(start: date, end: date) -> list[CalendarDay]:
    """Gera todas as datas do intervalo, inclusive finais de semana."""
    if end < start:
        raise ValueError("A data final do calendário não pode ser anterior à inicial")

    number_of_days = (end - start).days + 1
    return [CalendarDay(start + timedelta(days=offset)) for offset in range(number_of_days)]
