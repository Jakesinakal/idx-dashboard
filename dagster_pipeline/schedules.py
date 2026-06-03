"""
dagster_pipeline/schedules.py
------------------------------
Defines the Dagster job and schedule for the finance ETL pipeline.

Schedule:
    Cron:      "0 1 * * 1-5"  →  every Monday–Friday at 01:00 UTC
    Equivalent: 08:00 WIB (Western Indonesia Time, UTC+7)

Each scheduled run uses a 2-day lookback window so that only incremental
data is fetched. Manual / backfill runs use the DateRangeConfig defaults
(2 years) configured directly in the Dagster UI or CLI.
"""

from datetime import datetime, timedelta

from dagster import (
    AssetSelection,
    RunRequest,
    ScheduleDefinition,
    define_asset_job,
    schedule,
)

# ---------------------------------------------------------------------------
# Job definition — selects every asset in the repository
# ---------------------------------------------------------------------------

finance_etl_job = define_asset_job(
    name="finance_etl_job",
    selection=AssetSelection.all(),
    description=(
        "Full finance ETL pipeline: extract from Yahoo Finance and FRED, "
        "upload raw files to GCS, transform and join, load to BigQuery."
    ),
)

# ---------------------------------------------------------------------------
# Schedule — weekdays at 08:00 WIB with a 2-day incremental lookback
# ---------------------------------------------------------------------------

@schedule(
    name="weekday_8am_wib_schedule",
    cron_schedule="0 1 * * 1-5",
    job=finance_etl_job,
    execution_timezone="UTC",
    description="Triggers the ETL pipeline every weekday at 08:00 WIB (01:00 UTC).",
)
def weekday_finance_schedule(context) -> RunRequest:
    """
    Returns a RunRequest with a 2-day date window for incremental daily loads.
    The run_config overrides the DateRangeConfig defaults on all extract assets.
    """
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=2)).strftime("%Y-%m-%d")

    print(
        f"[Schedule] Triggering ETL run: {start_date} → {end_date}"
    )

    run_config = {
        "ops": {
            "extract_ihsg": {
                "config": {"start_date": start_date, "end_date": end_date}
            },
            "extract_fred": {
                "config": {"start_date": start_date, "end_date": end_date}
            },
            "extract_currency": {
                "config": {"start_date": start_date, "end_date": end_date}
            },
            "extract_news": {
                "config": {"start_date": start_date, "end_date": end_date}
            },
        }
    }

    return RunRequest(run_config=run_config)
