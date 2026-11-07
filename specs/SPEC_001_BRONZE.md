# SPEC 001 — Pipeline de Dados Econômicos | Camada Bronze

**Projeto:** Pipeline de Indicadores Econômicos Brasileiros  
**Versão de referência:** 1.2  
**Etapa:** 01 — Ingestão de Dados

## Escopo implementado

Ingestão dos indicadores Meta Selic (SGS 432), IPCA (SGS 433), dólar americano — venda — diário (SGS 1) e CDI anualizado (SGS 4389), entre `01/01/2023` e a data da execução.

O pipeline mantém os campos `data` e `valor` como strings, preserva a resposta JSON e o corpo HTTP bruto, gera Parquet válido, calcula SHA-256 e persiste o histórico no PostgreSQL.

## Destino

- Database: `db_emp_dados_junior`
- Schema: `bronze`
- Arquivos e metadados: `bronze.tb_arquivos_parquet`
- Auditoria: `bronze.tb_log_ingestao`

## Regras essenciais

- Exatamente uma tentativa por indicador e no máximo quatro requisições por execução.
- Nenhum retry ou redirecionamento automático.
- Sem conversão de datas ou valores, deduplicação, agregação ou regra de negócio.
- Persistência transacional do arquivo e do respectivo log de sucesso.
- Falhas isoladas por indicador, com status `SUCESSO`, `FALHA` ou `SEM_DADOS`.
- Credenciais carregadas exclusivamente do `.env`.
- Cópias locais temporárias não são versionadas.

Consulte o documento original da SPEC 001 fornecido para o curso para os requisitos, critérios de aceite e itens fora do escopo completos.
