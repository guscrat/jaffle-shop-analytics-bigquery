# dbt Fundamentals — Jaffle Shop (BigQuery edition)

Projeto do curso dbt Fundamentals, originalmente rodado no dbt Cloud com
Snowflake. Passou por duas migrações desde então: primeiro para **DuckDB
local** (só para estudo, sem depender de warehouse na nuvem) e agora para o
**sandbox do BigQuery**, então o setup precisa de alguns passos manuais antes
do primeiro `dbt run`. O projeto também pode ser rodado via **Docker**
(ver [Setup](#setup)).

## Resultado: dashboard de clientes

O pipeline termina em um dashboard no **Looker Studio** que lê as models
de marts direto do BigQuery. Os dados brutos saem do sistema da loja e do gateway de
pagamento e viram os indicadores que o time de negócio acompanha.

[![Dashboard Jaffle Shop no Looker Studio](assets/dashboard.png)](https://datastudio.google.com/s/lUn7P9Hb7WE)

🔗 **[Abrir o dashboard interativo](https://datastudio.google.com/s/lUn7P9Hb7WE)**

| Indicador | Valor | De onde vem |
|---|---|---|
| Clientes | 100 | `dim_customers` |
| Ordens | 99 | `fct_orders` |
| Faturamento | 1.672 | `sum(fct_orders.amount)`: só pagamentos com status `success` |
| Ticket médio | 16,89 | faturamento ÷ ordens |
| Ordens por mês | jan–abr/2018 | `fct_orders.order_date` agregado por mês |

### O que o dbt garante por trás de cada número

- **Faturamento real, não faturamento "tentado"**: `fct_orders` soma apenas
  pagamentos com `payment_status = 'success'`. Pagamentos que falharam não
  inflam a receita.
- **Unidade correta**: o Stripe registra valores em centavos, e a staging
  (`stg_strip__payments`) converte para a unidade monetária uma única vez.
  Todo consumidor downstream (dashboard, `dim_customers.lifetime_value`) já
  recebe o valor certo.
- **Uma única fonte da verdade**: o dashboard não tem SQL próprio nem regra
  de negócio escondida em campo calculado. As regras ficam versionadas e
  testadas no dbt (`dbt test`), e o Looker Studio só apresenta.
- **Pipeline reprodutível**: `load_raw.py -> dbt run -> dbt test` é
  orquestrado pelo Airflow (ver [Orquestração](#orquestração)), então o
  dashboard reflete dados atualizados sem passo manual.

```
CSVs brutos ──► BigQuery (jaffle_shop, stripe)
                    │
                    ▼
            staging (stg_*)  ── limpeza, renomeação, centavos → moeda
                    │
                    ▼
     marts (fct_orders, dim_customers) ── regras de negócio + testes
                    │
                    ▼
            Looker Studio (dashboard)
```

> Abril/2018 aparece com poucas ordens porque o dataset de exemplo termina
> no início do mês. Não é queda de vendas.

## Histórico de migrações

### Snowflake → DuckDB

O curso original usa dbt Cloud + Snowflake, que dependem de um data warehouse
gerenciado na nuvem — bom para o contexto do curso, mas overkill para rodar
o projeto localmente só para estudo. Troquei para DuckDB para poder:

- Rodar o pipeline inteiro (dbt-core + banco) na minha máquina, sem depender
  de credenciais de nuvem ou de um trial que expira.
- Entender melhor o que o dbt Cloud fazia "por trás" — profile, adapter,
  conexão — configurando tudo isso manualmente.
- Ter um projeto reprodutível por qualquer pessoa com Python instalado,
  sem precisar de conta em nenhum data warehouse.

A troca não foi só de connection string: exigiu trocar o adapter
(`dbt-snowflake` → `dbt-duckdb`), reconstruir a camada de dados brutos
(`load_raw.py`, já que não há mais um schema `RAW` pré-populado no
warehouse) e ajustar um mismatch de nome de tabela/source que só apareceu
depois da migração (`stripe.payments` → `stripe.payment`).

### DuckDB → BigQuery

O DuckDB é ótimo para estudar dbt sem fricção, mas roda tudo num arquivo
local — nenhuma das partes "de nuvem" de um projeto de dados real (auth,
projeto/dataset, load jobs, etc.) aparece na prática. Migrei para o
**sandbox do BigQuery** para treinar com um warehouse de nuvem de verdade:

- Autenticação via `gcloud auth application-default login` em vez de um
  arquivo de banco local.
- Dados brutos carregados via *load jobs* do BigQuery (`load_raw.py` agora
  baixa os CSVs, monta DataFrames com pandas e sobe com
  `google-cloud-bigquery`), em vez de `read_csv_auto` direto no DuckDB.
- Datasets do BigQuery (`jaffle_shop`, `stripe`) no lugar dos schemas
  attachados por arquivo do DuckDB — não existe mais um database `raw`
  separado, então os `sources.yml` perderam o campo `database: raw`.
- Um ajuste de tipo que o BigQuery exige e o DuckDB deixava passar:
  `order_date` precisou de `cast(... as date)` explícito em
  `stg_jaffle_shop__orders.sql`.

O adapter trocou de `dbt-duckdb` para `dbt-bigquery`, e o profile passou a
se chamar `jaffle_shop` (antes `default`).

### Containerização com Docker

Para não depender do Python/uv instalado na máquina, o projeto ganhou um
`Dockerfile` e um `compose.yaml`. No container, a autenticação deixa de ser
o login pessoal do `gcloud` e passa a ser uma **service account**:

- O profile do container fica versionado em `profiles/profiles.yml`
  (`method: service-account`), lendo projeto, dataset e caminho da chave de
  variáveis de ambiente (`env_var(...)`) definidas no `.env`.
- A chave JSON fica em `.secrets/sa.json`, montada como volume `read-only`
  só em runtime. Ela é ignorada pelo `.gitignore` e pelo `.dockerignore`,
  então nunca vai para o repositório nem para a imagem.
- O `load_raw.py` passou a ler o projeto de `GCP_PROJECT` em vez de uma
  constante fixa no código, para usar o mesmo projeto que o dbt.

## Arquitetura

- **BigQuery (projeto sandbox)** — os dados brutos e as models materializadas
  vivem em um projeto do GCP (ex.: `jaffle-shop-bq`, região `US`), não mais
  em arquivos locais.
- Datasets `jaffle_shop` e `stripe` — contêm as tabelas brutas
  (`jaffle_shop.customers`, `jaffle_shop.orders`, `stripe.payment`),
  recriadas pelo `load_raw.py` via load job (`WRITE_TRUNCATE`).
- As models de staging/marts do dbt são materializadas no mesmo projeto, no
  `dataset` configurado no `profiles.yml`. Use um dataset **separado** dos
  dados brutos (ex.: `dbt_dev`), para não misturar models com tabelas raw.

## Setup

Há duas formas de rodar o projeto, e cada uma autentica no BigQuery de um
jeito:

| | Docker | Local |
|---|---|---|
| Autenticação | service account (`.secrets/sa.json`) | seu login (`gcloud auth application-default login`) |
| Profile do dbt | `profiles/profiles.yml` (versionado) | `~/.dbt/profiles.yml` (fora do repositório) |
| Dependências | dentro da imagem | `uv sync` na sua máquina |

### Opção A: Docker

O passo a passo completo está no **[README.Docker.md](README.Docker.md)**.
Em resumo:

```bash
cp .env.example .env              # preencha GCP_PROJECT e GCP_DATASET
# copie a chave da service account para .secrets/sa.json
docker compose up --build         # build + dbt debug
docker compose run --rm dbt uv run load_raw.py
docker compose run --rm dbt uv run dbt build
```

### Opção B: Local

#### 1. Instalar as dependências

```bash
uv sync
source .venv/bin/activate
```

#### 2. Autenticar no GCP

```bash
gcloud auth application-default login
```

Isso gera as **Application Default Credentials (ADC)**: um arquivo de
credenciais OAuth salvo fora do repositório (em
`~/.config/gcloud/application_default_credentials.json`) que qualquer
biblioteca cliente do Google (`google-cloud-bigquery`, incluído) sabe
localizar sozinha, sem precisar apontar caminho nenhum no código.

É essa mesma credencial que autentica os dois pontos de acesso ao
BigQuery neste projeto:

- `load_raw.py`, porque `bigquery.Client(project=PROJECT, ...)` não recebe
  nenhuma credencial explícita — ele resolve via ADC por padrão.
- o dbt, porque o `profiles.yml` usa `method: oauth`, que também delega
  para as ADC.

> No Docker o `load_raw.py` é o mesmo: as ADC procuram primeiro a variável
> `GOOGLE_APPLICATION_CREDENTIALS`, que o `.env` aponta para a chave da
> service account. Por isso o script funciona nos dois modos sem mudar
> nada no código.

#### 3. Configurar o `profiles.yml`

Localmente o dbt lê o profile em `~/.dbt/profiles.yml` (fora do
repositório; o `profiles/profiles.yml` versionado é o do Docker). Crie/edite
esse arquivo com:

```yaml
jaffle_shop:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: jaffle-shop-bq   # id do seu projeto sandbox no GCP
      dataset: dbt_dev          # dataset das models (separado dos dados brutos)
      location: US
      threads: 4
```

#### 4. Carregar os dados brutos

Os dados fonte (customers, orders, payments) não vêm com o repositório.
O `load_raw.py` lê o id do projeto da variável `GCP_PROJECT`, que deve ser
o mesmo `project` do `profiles.yml`:

```bash
export GCP_PROJECT=jaffle-shop-bq
python load_raw.py
```

Isso cria os datasets `jaffle_shop` e `stripe` no projeto configurado, com
as tabelas esperadas pelos sources em `models/staging/*/`.

#### 5. Rodar o dbt

```bash
dbt debug   # confere se o adapter/profile foram encontrados
dbt build   # roda models e testes na ordem do DAG
```

## Orquestração

Este projeto também é orquestrado via Airflow no repositório
[`airflow-lab`](https://github.com/guscrat/airflow-lab), que encadeia
`load_raw.py -> dbt run -> dbt test` como um DAG.

## Links úteis

- [Documentação do dbt](https://docs.getdbt.com/docs/introduction)
- [Discourse do dbt](https://discourse.getdbt.com/) — perguntas e respostas frequentes
- [Comunidade dbt](https://getdbt.com/community)
- [Eventos do dbt](https://events.getdbt.com)
- [Blog do dbt](https://blog.getdbt.com/) — novidades e boas práticas
