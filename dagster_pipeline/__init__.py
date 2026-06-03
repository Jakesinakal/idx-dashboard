"""
dagster_pipeline/__init__.py
-----------------------------
Entry point for the Dagster repository.

Registers all assets, asset checks, jobs, schedules, and sensors
into a single Definitions object discovered via workspace.yaml.
"""

from dagster import Definitions, load_asset_checks_from_modules, load_assets_from_modules

from dagster_pipeline import asset_checks, assets
from dagster_pipeline.schedules import finance_etl_job, weekday_finance_schedule
from dagster_pipeline.sensors import etl_failure_sensor

all_assets = load_assets_from_modules([assets])
all_checks = load_asset_checks_from_modules([asset_checks])

defs = Definitions(
    assets=all_assets,
    asset_checks=all_checks,
    jobs=[finance_etl_job],
    schedules=[weekday_finance_schedule],
    sensors=[etl_failure_sensor],
)
