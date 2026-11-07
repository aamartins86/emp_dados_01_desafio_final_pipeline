# SPEC 003 — Modelagem Dimensional e Estruturação Analítica | Camada Ouro

**Projeto:** Pipeline de Indicadores Econômicos Brasileiros  
**Versão:** 1.1  
**Status:** Especificação para desenvolvimento  
**Arquitetura:** Medallion (Bronze, Prata e Ouro)  
**Etapa:** 03 — Modelagem Dimensional Prata → Ouro  
**Banco de dados:** db_emp_dados_junior  
**Schema de origem:** prata  
**Schema de destino:** ouro  
**Modelo de dados:** Star Schema (Modelo Estrela)

---

## 1. Objetivo

Desenvolver a camada Ouro do pipeline de indicadores econômicos brasileiros, utilizando os dados previamente tratados e normalizados da camada Prata.

A camada Ouro deverá disponibilizar exclusivamente tabelas analíticas estruturadas em um modelo dimensional, permitindo que o time de Business Intelligence utilize os dados diretamente na construção de dashboards e relatórios.

O modelo deverá possuir:

- Tabelas fato e dimensão.
- Chaves primárias (Primary Keys — PK).
- Chaves estrangeiras (Foreign Keys — FK).
- Chaves substitutas (Surrogate Keys).
- Relacionamentos com cardinalidade 1:N.
- Integridade referencial.
- Granularidade definida.
- Dados sem duplicidades.
- Atributos descritivos para filtros.
- Estrutura otimizada para consultas analíticas.

**Diretriz principal:** o schema ouro deverá conter somente tabelas destinadas ao consumo analítico pelo time de BI.

Não deverão ser criadas tabelas de logs, auditoria, rejeições, controle de execução ou processamento na camada Ouro.

## 2. Escopo

### 2.1. Incluído

1. Leitura dos dados normalizados da camada Prata.
2. Criação do schema ouro no PostgreSQL.
3. Criação das tabelas dimensão.
4. Criação da tabela fato.
5. Definição da granularidade da fato.
6. Implementação de chaves primárias.
7. Implementação de chaves estrangeiras.
8. Definição das chaves de negócio.
9. Implementação das chaves substitutas.
10. Definição de relacionamentos.
11. Validação de integridade referencial.
12. Eliminação de duplicidades no destino.
13. Atualização de registros existentes.
14. Preparação dos dados para consumo pelo BI.

### 2.2. Não incluído

- Consumo de APIs externas.
- Transformações de dados brutos.
- Deduplicação de registros na Bronze.
- Alterações nas tabelas da Prata.
- Criação de tabelas de logs.
- Criação de tabelas de auditoria.
- Criação de tabelas de controle de carga.
- Criação de tabelas de rejeição.
- Construção de dashboards.
- Criação de medidas DAX.
- Indicadores econômicos derivados.

As rotinas técnicas poderão registrar logs de execução fora do schema ouro, sem criar tabelas operacionais nessa camada.

## 3. Fonte dos Dados

**Banco:** db_emp_dados_junior  
**Schema de origem:** prata

### Tabelas utilizadas

| Tabela | Finalidade |
|---|---|
| prata.tb_indicadores_economicos | Dados econômicos normalizados |
| prata.tb_dim_indicador | Cadastro dos indicadores |

A camada Ouro deverá utilizar somente registros válidos e consolidados da Prata.

Não deverá realizar novas requisições à API do Banco Central.

## 4. Estrutura Dimensional

O modelo dimensional será composto exclusivamente por três tabelas:

| Tabela | Classificação | Finalidade |
|---|---|---|
| ouro.dim_calendario | Dimensão | Análises e filtros temporais |
| ouro.dim_indicador | Dimensão | Classificação dos indicadores econômicos |
| ouro.fct_indicadores_economicos | Fato | Armazenamento dos valores econômicos |

### Organização lógica

```text
db_emp_dados_junior
│
└── ouro
    │
    ├── dim_calendario
    │
    ├── dim_indicador
    │
    └── fct_indicadores_economicos
```

Não será permitida a criação de tabelas técnicas auxiliares permanentes no schema ouro.

## 5. Padrão de Nomenclatura

Os objetos deverão seguir a seguinte convenção:

| Objeto | Padrão |
|---|---|
| Schema | ouro |
| Dimensões | dim_ |
| Fatos | fct_ |
| Chaves primárias | id_ |
| Chaves estrangeiras | id_ |
| Campos descritivos | nome_, descricao_ |
| Datas | data_ |
| Valores numéricos | valor_ |
| Chaves de negócio | codigo_ |

Todos os nomes físicos deverão utilizar letras minúsculas, sem espaços e sem caracteres especiais.

## 6. Dimensão Calendário

**Tabela:** ouro.dim_calendario

### Objetivo

Disponibilizar atributos de calendário para permitir análises temporais e segmentações nos dashboards.

### Estrutura

| Coluna | Tipo PostgreSQL | Regra |
|---|---|---|
| id_data | INTEGER | PRIMARY KEY |
| data | DATE | UNIQUE NOT NULL |
| dia | SMALLINT | NOT NULL |
| mes | SMALLINT | NOT NULL |
| nome_mes | VARCHAR(20) | NOT NULL |
| trimestre | SMALLINT | NOT NULL |
| ano | INTEGER | NOT NULL |
| ano_mes | INTEGER | NOT NULL |
| mes_ano | VARCHAR(20) | NOT NULL |
| dia_semana | SMALLINT | NOT NULL |
| nome_dia_semana | VARCHAR(20) | NOT NULL |
| fim_de_semana | BOOLEAN | NOT NULL |

### Regras de negócio

- id_data deverá utilizar o formato numérico YYYYMMDD.
- Cada data deverá possuir um único registro.
- nome_mes deverá ser apresentado em português, com a primeira letra maiúscula.
- mes_ano deverá utilizar um formato adequado para exibição, como Jan/2026.
- ano_mes deverá utilizar YYYYMM para ordenação.
- O calendário iniciará em 01/01/2020.
- A geração deverá contemplar as datas necessárias para os indicadores disponíveis e permitir extensão até a data atual.
- A dimensão deverá possuir datas contínuas, incluindo finais de semana e feriados.
- A ausência de observações econômicas não deverá impedir a existência de datas na dimensão.

### Chave primária

`PRIMARY KEY (id_data)`

### Chave de negócio

`UNIQUE (data)`

## 7. Dimensão Indicador

**Tabela:** ouro.dim_indicador

### Objetivo

Concentrar as informações descritivas dos indicadores econômicos utilizados nos dashboards.

### Estrutura

| Coluna | Tipo PostgreSQL | Regra |
|---|---|---|
| id_indicador | INTEGER GENERATED BY DEFAULT AS IDENTITY | PRIMARY KEY |
| codigo_sgs | INTEGER | UNIQUE NOT NULL |
| nome_indicador | VARCHAR(150) | NOT NULL |
| unidade_medida | VARCHAR(50) | NOT NULL |
| periodicidade | VARCHAR(20) | NOT NULL |
| ativo | BOOLEAN | NOT NULL |

### Indicadores previstos

| Código SGS | Indicador |
|---|---|
| 432 | Meta Selic |
| 433 | IPCA |
| 1 | Dólar — Série cambial |
| 4389 | CDI anualizado |

Os nomes completos e as unidades deverão ser herdados da dimensão validada na Prata.

### Regras de negócio

- Cada codigo_sgs deverá existir uma única vez.
- id_indicador será a chave primária substituta.
- codigo_sgs será a chave natural de negócio.
- Os IDs deverão permanecer estáveis após atualizações.
- Alterações descritivas deverão utilizar SCD Tipo 1.
- A dimensão deverá ser carregada antes da tabela fato.
- Não deverão ser criadas versões históricas para alterações cadastrais nesta SPEC.

### Chave primária

`PRIMARY KEY (id_indicador)`

### Chave de negócio

`UNIQUE (codigo_sgs)`

## 8. Tabela Fato — Indicadores Econômicos

**Tabela:** ouro.fct_indicadores_economicos

### Objetivo

Disponibilizar os valores econômicos para análises por indicador e período.

### Granularidade

Uma observação por indicador econômico e data de referência.

A granularidade original da fonte deverá ser respeitada:

- Séries diárias manterão suas datas de observação.
- Séries mensais manterão suas datas de referência.
- Não deverão ser geradas observações artificiais para datas sem dados.

### Estrutura

| Coluna | Tipo PostgreSQL | Regra |
|---|---|---|
| id_fato | BIGINT GENERATED BY DEFAULT AS IDENTITY | PRIMARY KEY |
| id_indicador | INTEGER | FOREIGN KEY NOT NULL |
| id_data | INTEGER | FOREIGN KEY NOT NULL |
| valor_indicador | NUMERIC(20,8) | NOT NULL |

### Chave primária

`PRIMARY KEY (id_fato)`

### Chaves estrangeiras

`FOREIGN KEY (id_indicador) REFERENCES ouro.dim_indicador(id_indicador)`

`FOREIGN KEY (id_data) REFERENCES ouro.dim_calendario(id_data)`

### Chave composta de unicidade

`UNIQUE (id_indicador, id_data)`

### Regras de negócio

- Cada indicador poderá possuir apenas um registro por data de referência.
- Registros repetidos não deverão gerar novas linhas na fato.
- O valor deverá ser obtido da camada Prata.
- Alterações de valores na Prata deverão ser refletidas na Ouro.
- O id_fato deverá permanecer estável quando um valor for atualizado.
- Todas as chaves estrangeiras deverão possuir correspondência nas dimensões.
- A fato não deverá conter atributos descritivos já existentes nas dimensões.
- A fato não deverá armazenar informações de logs, arquivos ou execuções de ingestão.

### Natureza do valor

O campo valor_indicador não deverá ser considerado uma medida aditiva universal.

Os indicadores possuem unidades e significados econômicos distintos.

A soma indiscriminada dos valores não representa uma métrica economicamente válida.

## 9. Relacionamentos

Os relacionamentos deverão ser criados diretamente no PostgreSQL.

| Dimensão | PK | Fato | FK | Cardinalidade |
|---|---|---|---|---|
| dim_calendario | id_data | fct_indicadores_economicos | id_data | 1:N |
| dim_indicador | id_indicador | fct_indicadores_economicos | id_indicador | 1:N |

### Regras

- Todos os relacionamentos deverão possuir integridade referencial.
- Não poderão existir registros órfãos.
- Não poderão existir chaves estrangeiras nulas.
- Não serão utilizados relacionamentos muitos-para-muitos.
- O modelo deverá permitir filtragem das observações pelas dimensões.

Para consumo no Power BI, os relacionamentos deverão ser configurados preferencialmente com direção de filtro única, da dimensão para a fato.

## 10. Regras de Carregamento

A carga deverá seguir a ordem:

1. Dimensão Calendário.
2. Dimensão Indicador.
3. Tabela Fato.

### 10.1. Dimensões

Deverão ser inseridos somente registros ainda inexistentes.

Quando houver alterações descritivas na dimensão Indicador, os atributos deverão ser atualizados sem alteração da chave primária.

### 10.2. Tabela Fato

Deverá ser utilizada uma estratégia de UPSERT considerando a chave composta:

`id_indicador + id_data`

**Registro inexistente:** inserir.

**Registro existente com mesmo valor:** manter sem alteração.

**Registro existente com valor diferente:** atualizar somente o valor, preservando o id_fato.

### 10.3. Reexecução

O processo poderá ser executado repetidamente sem duplicar registros.

A carga deverá produzir o mesmo conjunto de observações quando os dados de origem não forem alterados.

### 10.4. Carga completa

A rotina deverá permitir a reconciliação completa da Ouro com a Prata.

Não deverá utilizar TRUNCATE ou recriar chaves primárias como estratégia padrão, evitando a alteração desnecessária dos identificadores dimensionais.

### 10.5. Atualização incremental

A implementação poderá utilizar os campos de atualização da Prata para identificar novos valores.

Quando não houver uma estratégia incremental confiável, deverá ser utilizada a reconciliação completa por UPSERT, considerando o volume reduzido do projeto.

Nenhuma tabela permanente de controle de processamento deverá ser criada no schema ouro.

## 11. Integridade Referencial e Índices

### Integridade

O PostgreSQL deverá garantir:

- PRIMARY KEY em todas as tabelas.
- FOREIGN KEY entre fato e dimensões.
- UNIQUE nas chaves de negócio.
- NOT NULL nos campos obrigatórios.
- Compatibilidade de tipos entre PK e FK.

### Índices

Deverão ser implementados índices necessários para relacionamentos e consultas analíticas.

Prioridades:

- Índices das chaves primárias.
- Unicidade de codigo_sgs.
- Unicidade de data.
- Índice único composto de id_indicador e id_data.
- Avaliação de índice adicional em id_data para consultas temporais.

Não deverão ser criados índices redundantes em colunas já cobertas adequadamente por restrições existentes.

## 12. Consultas e Consumo pelo BI

A camada Ouro deverá permitir:

- Consultar valores por indicador.
- Filtrar observações por ano.
- Filtrar observações por mês.
- Analisar valores por trimestre.
- Consultar séries históricas.
- Comparar visualmente indicadores.
- Segmentar por unidade de medida.
- Segmentar por periodicidade.
- Identificar o último valor disponível por indicador.

### Exemplo de estrutura analítica esperada

| Data | Indicador | Unidade | Valor |
|---|---|---|---|
| 02/01/2023 | Meta Selic | % a.a. | 13,75 |
| 01/01/2023 | IPCA | % a.m. | 0,53 |
| 03/01/2023 | Dólar | R$/US$ | 5,36 |

*Dados ilustrativos, não necessariamente correspondentes às observações reais da API.*

O modelo deverá permitir a obtenção dessas informações por meio de JOIN entre a fato e as respectivas dimensões.

Não deverão ser criadas tabelas desnormalizadas adicionais nesta versão.

## 13. Requisitos Funcionais

| ID | Requisito |
|---|---|
| RF001 | Criar o schema ouro |
| RF002 | Criar dim_calendario |
| RF003 | Criar dim_indicador |
| RF004 | Criar fct_indicadores_economicos |
| RF005 | Implementar chaves primárias |
| RF006 | Implementar chaves estrangeiras |
| RF007 | Implementar chaves de negócio |
| RF008 | Garantir relacionamentos 1:N |
| RF009 | Garantir integridade referencial |
| RF010 | Garantir unicidade na fato |
| RF011 | Implementar UPSERT |
| RF012 | Preservar identificadores existentes |
| RF013 | Permitir reexecução idempotente |
| RF014 | Atualizar valores provenientes da Prata |
| RF015 | Disponibilizar estrutura para consumo BI |

## 14. Requisitos Não Funcionais

| ID | Requisito |
|---|---|
| RNF001 | Utilizar PostgreSQL |
| RNF002 | Utilizar Python e SQL para a carga |
| RNF003 | Utilizar configurações do .env |
| RNF004 | Preservar os dados da Prata |
| RNF005 | Manter modelo estrela |
| RNF006 | Garantir integridade referencial |
| RNF007 | Evitar duplicidades |
| RNF008 | Preservar chaves substitutas |
| RNF009 | Garantir reprocessamento idempotente |
| RNF010 | Utilizar nomes físicos em minúsculas |
| RNF011 | Manter somente tabelas analíticas na Ouro |
| RNF012 | Não criar tabelas de logs ou controle no schema ouro |

## 15. Critérios de Aceite

**CA001 — Estrutura dimensional**

O schema ouro deverá conter exclusivamente as três tabelas analíticas especificadas.

**CA002 — Chaves primárias**

Todas as tabelas deverão possuir PK válida e não nula.

**CA003 — Chaves estrangeiras**

A tabela fato deverá possuir FK válida para ambas as dimensões.

**CA004 — Relacionamentos**

Os relacionamentos deverão apresentar cardinalidade 1:N.

**CA005 — Unicidade**

Não poderão existir registros repetidos para a combinação id_indicador + id_data.

**CA006 — Idempotência**

Reexecutar a carga sem alterações na Prata não deverá produzir novas observações.

**CA007 — Atualização**

Valores alterados na Prata deverão ser refletidos corretamente na Ouro.

**CA008 — Integridade**

Não poderão existir registros órfãos na tabela fato.

**CA009 — Preservação**

As chaves primárias deverão permanecer estáveis após atualizações.

**CA010 — Modelo BI**

A estrutura deverá permitir a criação de relacionamentos entre fato e dimensões em ferramentas de BI.

**CA011 — Ausência de tabelas técnicas**

Não deverão existir tabelas de logs, controle de carga, auditoria ou rejeições no schema ouro.

**CA012 — Consistência**

O conjunto de observações da Ouro deverá corresponder aos registros válidos da Prata, respeitando a granularidade definida.

## 16. Cenários de Teste

### CT001 — Estrutura dimensional

Verificar a existência das três tabelas especificadas.

Resultado: todas as tabelas disponíveis no schema ouro.

### CT002 — Chaves primárias

Validar que cada tabela possui PK.

Resultado: identificadores únicos e não nulos.

### CT003 — Chaves estrangeiras

Verificar os relacionamentos entre a fato e as dimensões.

Resultado: todas as referências válidas.

### CT004 — Unicidade

Executar carga contendo observações repetidas.

Resultado: apenas um registro por indicador e data.

### CT005 — Reexecução

Executar novamente a carga sem alterações na Prata.

Resultado: nenhuma duplicidade.

### CT006 — Atualização de valor

Modificar um valor de origem e reprocessar.

Resultado: valor atualizado sem alteração do id_fato.

### CT007 — Calendário

Validar os atributos de ano, mês, trimestre e dia da semana.

Resultado: informações temporais corretas.

### CT008 — Dimensão Indicador

Validar códigos, nomes, unidades e periodicidades.

Resultado: cadastro consistente com a Prata.

### CT009 — Consumo analítico

Executar JOIN entre as três tabelas.

Resultado: dados disponíveis para uso em dashboards.

### CT010 — Ausência de tabelas técnicas

Consultar os objetos do schema ouro.

Resultado: somente as três tabelas analíticas previstas.

## 17. Tecnologias Previstas

| Tecnologia | Finalidade |
|---|---|
| PostgreSQL | Armazenamento dimensional |
| SQL | Criação de tabelas, PK, FK e UPSERT |
| Python | Orquestração do carregamento |
| Psycopg | Conexão PostgreSQL |
| python-dotenv | Configurações do ambiente |
| Power BI | Consumo do modelo dimensional |

## 18. Resultado Esperado

Ao final da implementação da SPEC 003, o banco de dados db_emp_dados_junior deverá disponibilizar uma camada Ouro composta exclusivamente por:

- ouro.dim_calendario
- ouro.dim_indicador
- ouro.fct_indicadores_economicos

O modelo deverá possuir chaves primárias, chaves estrangeiras, relacionamentos 1:N, integridade referencial e controle de unicidade.

A camada Ouro deverá ser destinada exclusivamente ao consumo analítico, sem tabelas operacionais de logs, auditoria, rejeições ou controle de execução.

O time de BI deverá conseguir conectar ferramentas analíticas às tabelas e construir dashboards utilizando um modelo estrela consistente, com dimensões para filtragem e uma fato central contendo os valores econômicos.

---
