# SPEC 004 — Portal Analítico de Indicadores Macroeconômicos

**Projeto:** Pipeline de Indicadores Econômicos Brasileiros  
**Versão:** 1.4  
**Status:** Referência visual aprovada para implementação  
**Escopo:** Página institucional, navegação e relatório analítico  
**Fonte analítica:** PostgreSQL — schema `ouro`

## 1. Objetivo

Construir uma aplicação web que apresente a arquitetura do projeto e permita
explorar os indicadores Selic, IPCA, Dólar e CDI em um relatório analítico.

A experiência terá duas partes integradas:

1. uma página de abertura explicando o pipeline Banco Central → Bronze → Prata
   → Ouro → Consumo;
2. um ambiente analítico com filtros, indicadores, gráficos e insights.

## 2. Referências visuais aprovadas

As imagens abaixo são referências de composição, hierarquia e identidade:

- [Arquitetura — versão final](../docs/images/arquitetura-projeto.png)
- [Relatório — versão final](../docs/images/relatorio-publico.png)

Os valores apresentados nos protótipos são ilustrativos. Na aplicação, todos
os valores e períodos deverão vir da camada Ouro.

## 3. Identidade visual

| Uso | Cor |
|---|---|
| Azul principal | `#1966AE` |
| Azul escuro | `#09376E` |
| Fundo principal | `#F0F7FE` |
| Cartões | `#FFFFFF` |
| Borda suave | `#D7E6F5` |
| Texto principal | `#09376E` |
| Texto secundário | `#4F6B8A` |
| Hover | `#E4F0FB` |
| Destaque leve | `#DCEEFF` |

Regras:

- utilizar fundo claro e cartões brancos;
- usar azul como identidade dominante;
- reservar cobre, prata e dourado para representar as camadas;
- não utilizar verde como cor dominante;
- aplicar sombras sutis, bordas arredondadas e bastante espaço em branco;
- utilizar `Inter`, com fallback para `system-ui, sans-serif`.

## 4. Página Arquitetura do Projeto — capa

### 4.1. Cabeçalho

- Título: **Arquitetura de Dados do Projeto**.
- Subtítulo: **Pipeline de indicadores Macro Econômicos Brasileiros**.
- O título e o subtítulo deverão permanecer centralizados nesta página.

### 4.2. Fluxo da arquitetura

A página deverá preservar cinco blocos horizontais:

1. **Origem de Dados**
   - API Banco Central;
   - Selic;
   - IPCA;
   - Dólar;
   - CDI.
2. **Bronze**
   - Camada de dados brutos;
   - Ingestão;
   - Dados brutos;
   - Histórico original;
   - Baixo tratamento.
3. **Prata**
   - Camada de refinamento;
   - Limpeza;
   - Padronização;
   - Tratamento;
   - Enriquecimento;
   - Qualidade.
4. **Ouro**
   - Camada analítica e dimensional;
   - Modelo dimensional;
   - Fatos e dimensões;
   - Indicadores;
   - Dados prontos para BI.
5. **Consumo**
   - Dashboards;
   - Power BI;
   - Relatórios;
   - Analytics;
   - Tomada de decisão.

Os blocos deverão ser conectados visualmente por setas da esquerda para a
direita.

### 4.3. Ação principal

Acima do bloco Consumo deverá existir o botão:

**Entrar no Relatório**

O botão deverá:

- utilizar o mesmo acabamento azul do cabeçalho Consumo;
- possuir texto branco e ícone de seta;
- navegar para a página Relatório;
- ser acessível por teclado;
- apresentar estados de hover, foco e pressionado.

### 4.4. Benefícios

A faixa inferior deverá apresentar:

- Governança;
- Escalabilidade;
- Confiabilidade;
- Performance analítica.

## 5. Shell do relatório

As páginas analíticas deverão utilizar um container principal branco sobre o
fundo `#F0F7FE`, com cantos arredondados e sombra suave.

### 5.1. Navegação

O relatório não deverá utilizar uma barra superior, preservando o espaço
vertical para os elementos analíticos. A ação **Arquitetura do Projeto** ficará
junto aos filtros e a capa disponibilizará a ação **Entrar no Relatório**.

## 6. Página Relatório

### 6.1. Cabeçalho da página

- Título: **Panorama Histórico**.
- Subtítulo: **Acompanhe 4 dos principais indicadores macroeconômicos**.
- Ambos deverão ficar alinhados à esquerda.
- O título deverá ter tamanho de página, entre `25px` e `31px` no desktop.
- Não utilizar título grande de hero nem alinhamento centralizado.
- Não exibir data e hora técnica da consulta no cabeçalho.

### 6.2. Filtros

A barra de filtros deverá conter:

- período inicial;
- período final;
- indicador;
- Exportar;
- Arquitetura do Projeto.

No desktop, título e filtros deverão compartilhar a mesma faixa horizontal.
Os filtros ocuparão o espaço livre à direita do título. O botão
**Arquitetura do Projeto** deverá ficar na extremidade direita e abrir a capa.

Os filtros deverão alterar automaticamente KPIs, gráfico e insights de maneira
coordenada, sem depender de um botão Atualizar.

### 6.3. KPIs

Exibir quatro cartões:

| KPI | Unidade esperada |
|---|---|
| Selic | percentual ao ano |
| IPCA | percentual ao mês |
| Dólar | reais por dólar |
| CDI | percentual ao ano |

Cada cartão deverá apresentar:

- nome;
- último valor disponível;
- data de referência;
- variação em relação à observação anterior;
- unidade;
- micrográfico quando houver dados suficientes.

Os valores não poderão ser somados ou comparados como se possuíssem a mesma
unidade econômica.

### 6.4. Gráfico principal

O gráfico deverá apresentar a série histórica do indicador selecionado.

Requisitos:

- linha temporal;
- tooltip com data, valor e unidade;
- zoom ou seleção de intervalo;
- legenda;
- estado vazio;
- estado de carregamento;
- tratamento de erro;
- exportação da visualização ou dos dados.

### 6.5. Painel de insights

O painel lateral direito deverá exibir informações derivadas do período
selecionado, como:

- último valor;
- maior e menor valor;
- variação no período;
- direção da tendência;
- data da última atualização;
- explicação breve da unidade do indicador.

Insights deverão ser determinísticos e calculados a partir dos dados, sem
afirmações econômicas não sustentadas.

## 7. Escopo de navegação

O portal deverá possuir somente duas áreas:

1. **Relatório:** página inicial com filtros, KPIs, série histórica e insights;
2. **Arquitetura do Projeto:** segunda página com a capa e o pipeline.

Não deverão existir abas para Gerência, Indicadores Históricos ou Regras nesta
versão.

## 8. Fonte de dados

A aplicação deverá consultar exclusivamente:

- `ouro.dim_calendario`;
- `ouro.dim_indicador`;
- `ouro.fct_indicadores_economicos`.

Relacionamento analítico:

```text
dim_calendario 1 ─── N fct_indicadores_economicos N ─── 1 dim_indicador
```

Não consumir diretamente a API do Banco Central no frontend e não consultar
as camadas Bronze ou Prata para montar os relatórios.

## 9. Componentes reutilizáveis

- `AppShell`;
- `TopNavigation`;
- `ArchitectureSection`;
- `ReportEntryButton`;
- `PageHeader`;
- `FilterBar`;
- `KpiCard`;
- `ChartCard`;
- `InsightPanel`;
- `StatsCard`;
- `LoadingState`;
- `EmptyState`;
- `ErrorState`.

## 10. Responsividade

### Desktop

- navegação horizontal completa;
- quatro KPIs na mesma linha;
- gráfico e painel lateral em duas colunas.

### Tablet

- navegação compacta;
- KPIs em duas colunas;
- painel lateral abaixo do gráfico.

### Mobile

- navegação recolhível;
- KPIs em uma coluna;
- filtros empilhados;
- painel de insights após o gráfico;
- tabelas com rolagem horizontal acessível.

## 11. Acessibilidade

- contraste mínimo WCAG AA;
- foco visível;
- navegação completa por teclado;
- rótulos associados aos filtros;
- textos alternativos para imagens informativas;
- gráficos acompanhados de resumo textual ou tabela;
- não depender somente de cor para comunicar variação.

## 12. Requisitos funcionais

| ID | Requisito |
|---|---|
| RF001 | Exibir a arquitetura do pipeline |
| RF002 | Navegar da capa para Relatório |
| RF003 | Navegar somente entre Relatório e Arquitetura do Projeto |
| RF004 | Consultar os quatro indicadores da Ouro |
| RF005 | Filtrar por indicador e período |
| RF006 | Exibir último valor e variação anterior |
| RF007 | Exibir série histórica |
| RF008 | Exibir insights calculados |
| RF009 | Exibir estados de carregamento, vazio e erro |
| RF010 | Exportar dados filtrados |
| RF011 | Adaptar o layout a desktop, tablet e mobile |

## 13. Critérios de aceite

1. A página Projeto deverá corresponder à capa visual aprovada.
2. O botão Entrar no Relatório deverá abrir Relatório.
3. O relatório não deverá exibir o nome EconoData.
4. Panorama Histórico deverá ser compacto e alinhado à esquerda.
5. A navegação deverá alternar entre Relatório e Arquitetura do Projeto.
6. Os quatro KPIs deverão utilizar dados reais da Ouro.
7. Filtros deverão atualizar todos os componentes relacionados.
8. A página deverá conter gráfico principal e painel lateral.
9. Unidades e datas deverão ser apresentadas corretamente.
10. O frontend não deverá consultar Bronze, Prata ou Banco Central.
11. O layout deverá atender aos pontos de responsividade definidos.
12. O portal deverá atender aos requisitos básicos de acessibilidade.
13. A versão pública deverá consumir somente um snapshot da Ouro, sem expor credenciais.

## 14. Fora do escopo desta versão

- autenticação de usuários;
- edição de dados;
- ingestão manual;
- alterações nas camadas Bronze, Prata ou Ouro;
- previsões econômicas;
- recomendações financeiras;
- geração de insights por IA;
- medidas DAX ou arquivo Power BI.

## 15. Estratégia de implementação

1. criar o shell, tokens visuais e navegação;
2. implementar a página Projeto com a capa aprovada;
3. criar a consulta segura à camada Ouro;
4. implementar filtros e KPIs;
5. implementar gráfico e painel de insights;
6. validar responsividade e acessibilidade;
7. executar testes e revisão visual contra os protótipos.
