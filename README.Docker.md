# Python, dbt e BigQuery -- containerização com Docker

Projeto sendo containerizado com Docker para fácil execução e portabilidade.

Build de imagem com dbt (data build tool) e GCP BigQuery

## Pré-requisitos
Docker Compose v2
- Ambiente GCP BigQuery configurado
- Setup de GCP Service Account
- Configurar variáveis de ambiente (arquivo .env)

## Como fazer
- Colocar a chave JSON em .secrets/sa.json
- Criar um .env com as 4 variáveis de .env.example

## Segurança de credenciais
As credenciais do GCP (.secrets/sa.json) são montadas como volume com
`read-only` apenas em runtime e nunca são copiadas para a imagem Docker.
A pasta `.secrets/` é ignorada tanto no `.gitignore` quanto no
`.dockerignore`, garantindo que a credencial fica segura no seu PC e nunca
é commitada ou inclusa na imagem. Pode fazer push do código com segurança

# Antes de rodar o container, configurar as variáveis de ambiente
As variaveis de ambiente de .env são utilizadas no compose.yaml e
para validação de SA no load_raw.py
```env
GCP_PROJECT=gcp-project-name
GCP_DATASET=gcp-project-dataset
GCP_SA_KEYFILE=/app/secrets/sa.json
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/sa.json
```

# Como executar o Projeto
Siga os passos abaixo para rodar a aplicação usando Docker Compose

## 1. Clonar o repositório
Abra o terminal e clone o projeto
```bash
git clone https://github.com/guscrat/jaffle-shop-analytics-bigquery.git
cd jaffle-shop-analytics-bigquery
```

## 2. Criar imagem Docker com compose
Execute o comando abaixo para criar uma imagem desse projeto em seu Docker
e executar o comando padrão (uv run dbt debug), que verifica o setup correto
do projeto
```bash
docker compose up --build
```

## 3. Executando DBT

### a. Carregar os dados raw
```bash
docker compose run --rm dbt uv run load_raw.py
```

### b. Executar transformações e testes
```bash
docker compose run --rm dbt uv run dbt build
```