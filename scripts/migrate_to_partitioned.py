#!/usr/bin/env python3
"""
scripts/migrate_to_partitioned.py
----------------------------------
Recreates BigQuery tables with date-based partitioning (and clustering for
stock_performance) without dropping source data.

Tables:
  macro_economic_daily  → PARTITION BY DATE(date)
  stock_performance     → PARTITION BY DATE(date), CLUSTER BY ticker

Steps for each table:
  1. Count original rows as baseline.
  2. Create a backup copy  (<table>_backup).
  3. Create a new partitioned/clustered table (<table>_new) from the original.
  4. Verify <table>_new row count matches baseline.
  5. Swap: delete original, copy <table>_new → original name (partition info travels
     with the copy job).
  6. Verify final row count.
  7. Drop <table>_new.  <table>_backup is kept until you're confident and drop it
     manually.

Usage:
  source venv/bin/activate
  python scripts/migrate_to_partitioned.py
"""

import os
import sys

from dotenv import load_dotenv
from google.cloud import bigquery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", "credentials/gcp-credentials.json"
)

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
BQ_DATASET = os.environ.get("BQ_DATASET", "financial_data")

# DDL templates for each table.
# {project}, {dataset}, {table} are filled at runtime.
_TABLE_DDL: dict[str, str] = {
    "macro_economic_daily": """
        CREATE OR REPLACE TABLE `{project}.{dataset}.{table}_new`
        PARTITION BY DATE(date)
        AS SELECT * FROM `{project}.{dataset}.{table}`
    """,
    "stock_performance": """
        CREATE OR REPLACE TABLE `{project}.{dataset}.{table}_new`
        PARTITION BY DATE(date)
        CLUSTER BY ticker
        AS SELECT * FROM `{project}.{dataset}.{table}`
    """,
}


def _count(client: bigquery.Client, table_id: str) -> int:
    rows = list(client.query(f"SELECT COUNT(*) AS n FROM `{table_id}`").result())
    return rows[0]["n"]


def migrate_table(client: bigquery.Client, table_name: str, ddl_template: str) -> None:
    p, d = GCP_PROJECT_ID, BQ_DATASET
    orig_id   = f"{p}.{d}.{table_name}"
    new_id    = f"{p}.{d}.{table_name}_new"
    backup_id = f"{p}.{d}.{table_name}_backup"

    print(f"\n{'=' * 60}")
    print(f"Table: {table_name}")
    print(f"{'=' * 60}")

    baseline = _count(client, orig_id)
    print(f"  Original rows:  {baseline:,}")

    # Step 1 — backup
    print(f"  Creating backup: {backup_id}")
    client.copy_table(orig_id, backup_id).result()
    backup_count = _count(client, backup_id)
    if backup_count != baseline:
        raise RuntimeError(f"Backup row mismatch: expected {baseline:,}, got {backup_count:,}")
    print(f"  Backup verified: {backup_count:,} rows")

    # Step 2 — build partitioned table
    ddl = ddl_template.format(project=p, dataset=d, table=table_name).strip()
    print(f"  Creating partitioned table: {new_id}")
    client.query(ddl).result()

    new_count = _count(client, new_id)
    print(f"  New table rows:  {new_count:,}")
    if new_count != baseline:
        client.delete_table(new_id, not_found_ok=True)
        raise RuntimeError(
            f"Row count mismatch for {table_name}_new: "
            f"expected {baseline:,}, got {new_count:,}. "
            f"Original table is untouched. Backup retained at {backup_id}."
        )
    print(f"  Row count OK: {new_count:,}")

    # Step 3 — swap
    print(f"  Swapping tables...")
    client.delete_table(orig_id)
    client.copy_table(new_id, orig_id).result()

    final_count = _count(client, orig_id)
    if final_count != baseline:
        raise RuntimeError(
            f"Final row count mismatch after swap: expected {baseline:,}, got {final_count:,}. "
            f"Restore from {backup_id}."
        )
    print(f"  Swap complete. Final rows: {final_count:,}")

    # Step 4 — clean up new (keep backup until manually dropped)
    client.delete_table(new_id)
    print(f"  Dropped intermediary: {new_id}")
    print(f"  Backup retained at:   {backup_id}  (drop manually when confident)")
    print(f"  Migration successful!")


def main() -> None:
    if not GCP_PROJECT_ID or not BQ_DATASET:
        sys.exit("ERROR: GCP_PROJECT_ID and BQ_DATASET must be set in .env")

    print(f"Project: {GCP_PROJECT_ID}")
    print(f"Dataset: {BQ_DATASET}")

    client = bigquery.Client(project=GCP_PROJECT_ID)

    for table_name, ddl in _TABLE_DDL.items():
        migrate_table(client, table_name, ddl)

    print("\nAll migrations complete.")
    print("When confident the data is correct, drop the backup tables:")
    for name in _TABLE_DDL:
        print(f"  bq rm -f {GCP_PROJECT_ID}:{BQ_DATASET}.{name}_backup")


if __name__ == "__main__":
    main()
