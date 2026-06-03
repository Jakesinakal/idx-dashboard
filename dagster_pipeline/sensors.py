"""
dagster_pipeline/sensors.py
----------------------------
Dagster sensors for the finance ETL pipeline.

etl_failure_sensor — fires on any run failure and logs:
  - run_id, job name, failed asset/step keys, truncated error message
"""

from dagster import DefaultSensorStatus, RunFailureSensorContext, run_failure_sensor


@run_failure_sensor(
    name="etl_failure_sensor",
    description="Logs run failures with the failed asset name and error message.",
    default_status=DefaultSensorStatus.RUNNING,
)
def etl_failure_sensor(context: RunFailureSensorContext) -> None:
    run = context.dagster_run

    # Collect per-step error details (step key == asset name for SDA pipelines)
    error_by_step: dict[str, str] = {
        event.step_key: event.event_specific_data.error.to_string()
        for event in context.get_step_failure_events()
        if event.step_key and event.event_specific_data
    }

    failed_assets = ", ".join(error_by_step.keys()) or "unknown"

    # Top-level run error (present even when no step-level data is available)
    run_error = (
        context.failure_event.message
        if context.failure_event and hasattr(context.failure_event, "message")
        else "no message"
    )

    context.log.error(
        f"[ETL Failure] "
        f"run_id={run.run_id[:8]} | "
        f"job={run.job_name} | "
        f"failed_assets=[{failed_assets}] | "
        f"error={run_error[:300]}"
    )

    # Log each step's full stack trace at debug level for post-mortem
    for step_key, trace in error_by_step.items():
        context.log.debug(f"[ETL Failure] {step_key} traceback:\n{trace}")
