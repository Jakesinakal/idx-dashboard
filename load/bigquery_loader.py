"""
load/bigquery_loader.py
-----------------------
Loads a pandas DataFrame into a BigQuery table.

Supported write modes:
    "append"   — adds new rows without touching existing data
    "truncate" — replaces the entire table on each run
    "merge"    — upserts via staging table: UPDATE matched rows, INSERT new rows.
                 Requires merge_keys to identify existing records.

Schema is auto-detected from the DataFrame. Credentials are loaded from
GOOGLE_APPLICATION_CREDENTIALS defined in .env.
"""

import os

import pandas as pd
from dotenv import load_dotenv
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", "credentials/gcp-credentials.json"
)

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
BQ_DATASET = os.environ.get("BQ_DATASET", "")

_WRITE_DISPOSITION = {
    "append":   bigquery.WriteDisposition.WRITE_APPEND,
    "truncate": bigquery.WriteDisposition.WRITE_TRUNCATE,
}


def _table_exists(client: bigquery.Client, table_id: str) -> bool:
    try:
        client.get_table(table_id)
        return True
    except NotFound:
        return False


def _load_staging(
    client: bigquery.Client,
    df: pd.DataFrame,
    staging_table_id: str,
) -> None:
    job_config = bigquery.LoadJobConfig(
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_dataframe(df, staging_table_id, job_config=job_config)
    job.result()


def _run_merge(
    client: bigquery.Client,
    df: pd.DataFrame,
    target_table_id: str,
    staging_table_id: str,
    merge_keys: list[str],
) -> int:
    cols = list(df.columns)
    non_key_cols = [c for c in cols if c not in merge_keys]

    join_cond  = " AND ".join(f"T.`{k}` = S.`{k}`" for k in merge_keys)
    update_set = ", ".join(f"T.`{c}` = S.`{c}`" for c in non_key_cols)
    insert_cols = ", ".join(f"`{c}`" for c in cols)
    insert_vals = ", ".join(f"S.`{c}`" for c in cols)

    merge_sql = f"""
        MERGE `{target_table_id}` AS T
        USING `{staging_table_id}` AS S
        ON {join_cond}
        WHEN MATCHED THEN
            UPDATE SET {update_set}
        WHEN NOT MATCHED THEN
            INSERT ({insert_cols})
            VALUES ({insert_vals})
    """

    job = client.query(merge_sql)
    job.result()
    return job.num_dml_affected_rows or 0


def load_to_bigquery(
    df: pd.DataFrame,
    table_name: str,
    mode: str = "merge",
    merge_keys: list[str] | None = None,
) -> dict:
    """
    Loads a DataFrame into a BigQuery table.

    Args:
        df:          DataFrame to load.
        table_name:  Destination table (without project/dataset prefix).
        mode:        "append", "truncate", or "merge".
        merge_keys:  Column(s) that uniquely identify a row. Required for mode="merge".

    Raises:
        ValueError: For invalid mode or missing merge_keys.
        Exception:  Propagates any BigQuery client error after logging.
    """
    valid_modes = {"append", "truncate", "merge"}
    if mode not in valid_modes:
        raise ValueError(f"[BigQuery] Invalid mode '{mode}'. Use one of: {valid_modes}")
    if mode == "merge" and not merge_keys:
        raise ValueError("[BigQuery] merge_keys must be provided when mode='merge'")

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{table_name}"
    print(f"[BigQuery] Loading {len(df)} rows into {table_id} (mode={mode})")

    try:
        client = bigquery.Client(project=GCP_PROJECT_ID)

        if mode in _WRITE_DISPOSITION:
            job_config = bigquery.LoadJobConfig(
                autodetect=True,
                write_disposition=_WRITE_DISPOSITION[mode],
            )
            job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
            job.result()
        else:
            staging_table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{table_name}_staging"
            print(f"[BigQuery] Loading staging: {staging_table_id}")
            _load_staging(client, df, staging_table_id)

            try:
                if not _table_exists(client, table_id):
                    # First run: promote staging directly to avoid a MERGE against a missing table
                    print(f"[BigQuery] Target does not exist; creating from staging.")
                    client.copy_table(staging_table_id, table_id).result()
                else:
                    affected = _run_merge(client, df, table_id, staging_table_id, merge_keys)
                    print(f"[BigQuery] Merge complete. Rows affected (inserts + updates): {affected}")
            finally:
                client.delete_table(staging_table_id, not_found_ok=True)
                print(f"[BigQuery] Dropped staging: {staging_table_id}")

        table = client.get_table(table_id)
        print(f"[BigQuery] Done. {table_id} now has {table.num_rows:,} total rows.")
        return {"total_rows": table.num_rows, "total_bytes": table.num_bytes}

    except Exception as e:
        print(f"[BigQuery] ERROR: {e}")
        raise
