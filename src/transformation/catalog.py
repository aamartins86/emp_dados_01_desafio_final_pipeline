"""Cadastro oficial das séries econômicas processadas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorDefinition:
    indicator_id: int
    sgs_code: int
    name: str
    unit: str
    periodicity: str


INDICATOR_CATALOG = {
    432: IndicatorDefinition(
        1,
        432,
        "Taxa de juros - Meta Selic definida pelo Copom",
        "Percentual ao ano",
        "Diária",
    ),
    433: IndicatorDefinition(
        2,
        433,
        "Índice nacional de preços ao consumidor-amplo (IPCA) - Var. % mensal",
        "Variação percentual mensal",
        "Mensal",
    ),
    1: IndicatorDefinition(
        3,
        1,
        "Taxa de câmbio - Livre - Dólar americano (venda) - diário",
        "Unidade monetária corrente por dólar americano",
        "Diária",
    ),
    4389: IndicatorDefinition(
        4,
        4389,
        "Taxa de juros - CDI em termos anuais (base 252)",
        "Percentual ao ano",
        "Diária",
    ),
}
