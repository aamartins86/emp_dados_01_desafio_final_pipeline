# SPEC 002 — Tratamento, Normalização e Deduplicação | Camada Prata

**Projeto:** Pipeline de Indicadores Econômicos Brasileiros  
**Versão:** 1.0  
**Etapa:** 02 — Transformação Bronze → Prata  
**Database:** `db_emp_dados_junior`  
**Origem:** schema `bronze`  
**Destino:** schema `prata`

## Objetivo

Transformar os arquivos Parquet preservados na Bronze em observações econômicas tipadas, validadas, rastreáveis e sem duplicidades, sem modificar a camada de origem nem consultar novamente a API do Banco Central.

## Contrato de transformação

| Origem | Destino | Tipo |
|---|---|---|
| `data` | `data_referencia` | `DATE` |
| `valor` | `valor` | `NUMERIC(20,8)` |
| metadado | `codigo_sgs` | `INTEGER` |
| metadado | `id_indicador` | `INTEGER` |
| metadado | `id_execucao_origem` | `UUID` |
| metadado | `id_arquivo_origem` | `BIGINT` |

Datas são convertidas estritamente de `DD/MM/YYYY`. Valores inválidos, nulos, fora de precisão ou com código SGS desconhecido são rejeitados sem substituição por zero ou criação de dados artificiais.

## Deduplicação e precedência

A chave natural é `codigo_sgs + data_referencia`. A versão vencedora é selecionada por:

1. maior data de ingestão Bronze;
2. maior identificador do arquivo de origem;
3. maior ordem da observação dentro do Parquet.

Valores idênticos não alteram a Prata. Uma versão mais recente com valor diferente atualiza a observação e registra o valor anterior no histórico.

## Tabelas

- `prata.tb_dim_indicador`
- `prata.tb_indicadores_economicos`
- `prata.tb_registros_rejeitados`
- `prata.tb_log_transformacao`
- `prata.tb_historico_alteracoes`
- `prata.tb_controle_processamento`

A tabela principal possui `UNIQUE (codigo_sgs, data_referencia)`.

## Modos de execução

### Incremental

Processa somente arquivos cujo par `id_arquivo_origem + hash_arquivo` ainda não tenha controle com status `SUCESSO`.

```powershell
python -B -m src.transformation.pipeline
```

### Reprocessamento completo

Relê todos os arquivos Bronze válidos, reaplica normalização e deduplicação e publica os resultados na mesma transação, preservando logs, controles e histórico.

```powershell
python -B -m src.transformation.pipeline --full
```

## Qualidade

- código SGS, data e valor obrigatórios;
- data e valor válidos;
- código cadastrado e unidade conhecida;
- hash e leitura do Parquet válidos;
- chave natural única;
- origem rastreável;
- rejeições registradas com o dado original e o motivo;
- nenhuma alteração ou exclusão na Bronze.

## Critérios de aceite

- tipos normalizados na Prata;
- nenhuma duplicidade pela chave natural;
- segunda execução incremental sem aumento de registros;
- atualização somente com precedência válida;
- histórico para valores revisados;
- logs e métricas em todas as execuções;
- controle dos arquivos processados;
- reprocessamento determinístico;
- conciliação entre lidos, válidos, duplicados, persistidos e rejeitados.

## Resultado de referência

Com duas ingestões Bronze equivalentes:

| Métrica | Resultado |
|---|---:|
| Arquivos lidos | 8 |
| Registros lidos | 6.766 |
| Registros válidos | 6.766 |
| Duplicidades removidas | 3.383 |
| Observações inseridas | 3.383 |
| Rejeições | 0 |

A repetição incremental selecionou zero arquivos. O reprocessamento completo manteve as 3.383 observações sem inserções ou atualizações.
