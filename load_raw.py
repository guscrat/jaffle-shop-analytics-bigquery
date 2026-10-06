"""
Carrega os CSVs públicos do jaffle shop como tabelas no BigQuery.
Versão BigQuery (sandbox) — substitui a versão DuckDB.

Pré-requisitos:
  uv add google-cloud-bigquery pandas pyarrow requests
  gcloud auth application-default login   # mesma auth do profiles.yml (oauth)

Sandbox-safe: usa load jobs (não streaming, não DML).
"""

import io
import os
from datetime import datetime, timezone

import pandas as pd
import requests
from google.cloud import bigquery

# ---------------------
PROJECT = os.environ["GCP_PROJECT"]   # id do projeto sandbox no GCP
LOCATION = "US"                       # sandbox roda em US (bate com o profiles.yml)
# ---------------------

BASE = "https://dbt-tutorial-public.s3.amazonaws.com"

client = bigquery.Client(project=PROJECT, location=LOCATION)

# datasets espelhando os schemas que existiam no raw.duckdb
for ds in ("jaffle_shop", "stripe"):
    client.create_dataset(bigquery.Dataset(f"{PROJECT}.{ds}"), exists_ok=True)
    print(f"dataset ok: {ds}")


def csv_to_df(filename: str) -> pd.DataFrame:
    """Baixa o CSV público pra memória e devolve como DataFrame."""
    resp = requests.get(f"{BASE}/{filename}", timeout=60)
    resp.raise_for_status()
    return pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig")


def load(df: pd.DataFrame, table: str) -> None:
    """Sobe o DataFrame pro BigQuery via load job (WRITE_TRUNCATE = CREATE OR REPLACE)."""
    job = client.load_table_from_dataframe(
        df,
        table,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()  # espera terminar
    print(f"{table}: {job.output_rows} linhas")


# timestamp único do batch, igual o current_timestamp fazia no DuckDB
now = datetime.now(timezone.utc)

# jaffle_shop.customers — sem coluna extra
load(csv_to_df("jaffle_shop_customers.csv"), f"{PROJECT}.jaffle_shop.customers")

# jaffle_shop.orders — + _etl_loaded_at
orders = csv_to_df("jaffle_shop_orders.csv")
orders["_etl_loaded_at"] = now
load(orders, f"{PROJECT}.jaffle_shop.orders")

# stripe.payment — + _batched_at
payment = csv_to_df("stripe_payments.csv")
payment["_batched_at"] = now
load(payment, f"{PROJECT}.stripe.payment")

print("Pronto! Raw carregado no BigQuery.")
