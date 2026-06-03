"""
dagster_pipeline/dbt_assets.py
-------------------------------
Registers dbt models as Dagster Software-Defined Assets.

Upstream dependencies are resolved via meta.dagster.asset_key in sources.yml:
  financial_data.stock_performance   → bq_stock_performance  (Dagster asset)
  financial_data.macro_economic_daily → bq_macro_economic_daily (Dagster asset)

DbtProject.prepare_if_dev() is called at import time so that `dagster dev`
automatically runs `dbt deps` (if packages are missing) and `dbt parse`
(to regenerate manifest.json) on startup.
"""

import os
from pathlib import Path

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets
from dotenv import load_dotenv

load_dotenv()

DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt"
_PROJECT_ROOT   = DBT_PROJECT_DIR.parent

# DbtCliResource spawns dbt as a subprocess with project_dir (dbt/) as CWD.
# A relative GOOGLE_APPLICATION_CREDENTIALS path would resolve to dbt/credentials/…
# which doesn't exist. Force it to absolute so the subprocess always finds the file.
_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials/gcp-credentials.json")
if not os.path.isabs(_creds):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_PROJECT_ROOT / _creds)

dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=DBT_PROJECT_DIR,
)
dbt_project.prepare_if_dev()

dbt_resource = DbtCliResource(
    project_dir=str(DBT_PROJECT_DIR),
    profiles_dir=str(DBT_PROJECT_DIR),
)


@dbt_assets(manifest=dbt_project.manifest_path)
def finance_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource) -> None:
    yield from dbt.cli(["build"], context=context).stream()
