from src.database.gold_repository import GOLD_TABLES, SILVER_REQUIRED_COLUMNS


def test_schema_ouro_permite_somente_tabelas_analiticas() -> None:
    assert GOLD_TABLES == {
        "dim_calendario",
        "dim_indicador",
        "fct_indicadores_economicos",
    }


def test_contrato_prata_contem_chaves_e_valor_da_fato() -> None:
    assert {"codigo_sgs", "data_referencia", "valor"}.issubset(
        SILVER_REQUIRED_COLUMNS["tb_indicadores_economicos"]
    )
