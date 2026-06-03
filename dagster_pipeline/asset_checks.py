"""
dagster_pipeline/asset_checks.py
---------------------------------
Dagster asset checks for bq_stock_performance and bq_macro_economic_daily.

Each check queries BigQuery directly and returns:
  - AssetCheckResult with passed/severity
  - metadata: violation_count (int) + sample_violations (markdown table)

Severity guide:
  ERROR  blocking=True  — structural / correctness violation; never expected in clean data
  WARN   blocking=False — anomaly worth investigating; may be legitimate (e.g. IPO halt)
"""

import os
import sys

import pandas as pd
from dagster import AssetCheckResult, AssetCheckSeverity, MetadataValue, asset_check
from dotenv import load_dotenv
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from config.universe import expected_stock_count  # noqa: E402  (needs sys.path above)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", "credentials/gcp-credentials.json"
)

_PROJECT = os.environ.get("GCP_PROJECT_ID", "")
_DATASET = os.environ.get("BQ_DATASET", "")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _tbl(name: str) -> str:
    return f"`{_PROJECT}.{_DATASET}.{name}`"


def _query_violations(
    client: bigquery.Client,
    violation_sql: str,
    sample_limit: int = 10,
) -> tuple[int, pd.DataFrame]:
    """Run violation_sql (no top-level ORDER BY/LIMIT), return (count, sample_df)."""
    count = list(
        client.query(f"SELECT COUNT(*) AS n FROM ({violation_sql})").result()
    )[0]["n"]
    if count == 0:
        return 0, pd.DataFrame()
    rows = list(
        client.query(f"SELECT * FROM ({violation_sql}) LIMIT {sample_limit}").result()
    )
    return count, pd.DataFrame([dict(r) for r in rows])


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No violations_"
    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
    body   = [
        "| " + " | ".join(str(v) for v in row) + " |"
        for _, row in df.iterrows()
    ]
    return "\n".join([header, sep, *body])


def _result(
    count: int,
    df: pd.DataFrame,
    severity: AssetCheckSeverity,
) -> AssetCheckResult:
    return AssetCheckResult(
        passed=count == 0,
        severity=severity,
        metadata={
            "violation_count":   MetadataValue.int(count),
            "sample_violations": MetadataValue.md(_md_table(df)),
        },
    )


def _table_missing(severity: AssetCheckSeverity) -> AssetCheckResult:
    return AssetCheckResult(
        passed=False,
        severity=severity,
        metadata={"error": MetadataValue.text("Table not found — run the asset first.")},
    )


# ---------------------------------------------------------------------------
# bq_stock_performance — ERROR checks (blocking)
# ---------------------------------------------------------------------------

@asset_check(asset="bq_stock_performance", name="close_positive", blocking=True)
def check_stock_close_positive() -> AssetCheckResult:
    sql = f"""
        SELECT date, ticker, name, close
        FROM {_tbl('stock_performance')}
        WHERE close <= 0
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.ERROR)
    return _result(count, df, AssetCheckSeverity.ERROR)


@asset_check(asset="bq_stock_performance", name="volume_non_negative", blocking=True)
def check_stock_volume_non_negative() -> AssetCheckResult:
    sql = f"""
        SELECT date, ticker, volume
        FROM {_tbl('stock_performance')}
        WHERE volume < 0
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.ERROR)
    return _result(count, df, AssetCheckSeverity.ERROR)


@asset_check(asset="bq_stock_performance", name="unique_date_ticker", blocking=True)
def check_stock_unique_date_ticker() -> AssetCheckResult:
    sql = f"""
        SELECT date, ticker, COUNT(*) AS duplicate_count
        FROM {_tbl('stock_performance')}
        GROUP BY date, ticker
        HAVING COUNT(*) > 1
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.ERROR)
    return _result(count, df, AssetCheckSeverity.ERROR)


# ---------------------------------------------------------------------------
# bq_stock_performance — WARN checks
# ---------------------------------------------------------------------------

@asset_check(asset="bq_stock_performance", name="daily_return_within_circuit_breaker")
def check_stock_return_range() -> AssetCheckResult:
    # IDX circuit breaker halts trading at ±35% single-session moves.
    # Values outside this range either signal a data error or an extraordinary event.
    sql = f"""
        WITH returns AS (
            SELECT
                date, ticker, close,
                LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close,
                SAFE_DIVIDE(
                    close - LAG(close) OVER (PARTITION BY ticker ORDER BY date),
                    LAG(close) OVER (PARTITION BY ticker ORDER BY date)
                ) * 100 AS return_pct
            FROM {_tbl('stock_performance')}
        )
        SELECT date, ticker, close, prev_close, ROUND(return_pct, 2) AS return_pct
        FROM returns
        WHERE ABS(return_pct) > 35
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.WARN)
    return _result(count, df, AssetCheckSeverity.WARN)


@asset_check(asset="bq_stock_performance", name="ticker_count_per_day")
def check_stock_ticker_count() -> AssetCheckResult:
    # Pipeline extracts the full tracked universe (LQ45 today; ^JKSE excluded
    # from this table). The expected count comes from config.universe so it
    # tracks the universe automatically. On a recent trading day, fewer tickers
    # means a fetch failed; more means an unexpected ticker slipped in.
    #
    # Scope to the last 14 days only: many LQ45 constituents IPO'd within the
    # 2-year backfill window, so older dates legitimately have fewer tickers and
    # would otherwise produce noise.
    expected = expected_stock_count()
    # date is stored as a STRING ('YYYY-MM-DD') in this table — wrap with DATE()
    # to compare against a DATE literal, matching the convention used by the
    # other date-based checks in this file.
    sql = f"""
        SELECT date, COUNT(DISTINCT ticker) AS ticker_count
        FROM {_tbl('stock_performance')}
        WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
        GROUP BY date
        HAVING COUNT(DISTINCT ticker) != {expected}
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.WARN)
    return _result(count, df, AssetCheckSeverity.WARN)


# ---------------------------------------------------------------------------
# bq_macro_economic_daily — ERROR check (blocking)
# ---------------------------------------------------------------------------

@asset_check(asset="bq_macro_economic_daily", name="ihsg_close_not_null", blocking=True)
def check_macro_ihsg_close_not_null() -> AssetCheckResult:
    # ihsg_close is the join base. A null means the ^JKSE row was missing
    # from the extract, which would corrupt every derived column for that date.
    sql = f"""
        SELECT date, ihsg_close
        FROM {_tbl('macro_economic_daily')}
        WHERE ihsg_close IS NULL
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.ERROR)
    return _result(count, df, AssetCheckSeverity.ERROR)


# ---------------------------------------------------------------------------
# bq_macro_economic_daily — WARN checks
# ---------------------------------------------------------------------------

@asset_check(asset="bq_macro_economic_daily", name="usd_idr_in_range")
def check_macro_usd_idr_range() -> AssetCheckResult:
    # IDR/USD has traded between ~13,000 and ~17,000 in the 2020–2025 window;
    # [13000, 20000] gives generous headroom for structural moves without
    # masking obvious data errors (e.g. raw value in wrong units).
    sql = f"""
        SELECT date, usd_idr
        FROM {_tbl('macro_economic_daily')}
        WHERE usd_idr < 13000 OR usd_idr > 20000
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.WARN)
    return _result(count, df, AssetCheckSeverity.WARN)


@asset_check(asset="bq_macro_economic_daily", name="no_weekend_dates")
def check_macro_no_weekends() -> AssetCheckResult:
    # IDX is closed on weekends; any Saturday/Sunday row is a bad join or
    # a yfinance timezone edge case.
    # BigQuery DAYOFWEEK: 1=Sunday, 7=Saturday
    sql = f"""
        SELECT date, EXTRACT(DAYOFWEEK FROM DATE(date)) AS day_of_week
        FROM {_tbl('macro_economic_daily')}
        WHERE EXTRACT(DAYOFWEEK FROM DATE(date)) IN (1, 7)
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.WARN)
    return _result(count, df, AssetCheckSeverity.WARN)


@asset_check(asset="bq_macro_economic_daily", name="fred_nulls_after_warmup")
def check_macro_fred_nulls_after_warmup() -> AssetCheckResult:
    # cpi_us and fed_rate are forward-filled from monthly FRED releases.
    # Leading nulls before the first FRED data point are expected and vary
    # depending on the backfill start date. Rather than a fixed calendar
    # threshold, we find the first date where FRED data actually exists and
    # flag any null after that — a genuine forward-fill failure.
    sql = f"""
        WITH first_fred AS (
            SELECT MIN(DATE(date)) AS first_valid_date
            FROM {_tbl('macro_economic_daily')}
            WHERE cpi_us IS NOT NULL AND fed_rate IS NOT NULL
        )
        SELECT m.date, m.cpi_us, m.fed_rate
        FROM {_tbl('macro_economic_daily')} m
        CROSS JOIN first_fred
        WHERE DATE(m.date) > first_fred.first_valid_date
          AND (m.cpi_us IS NULL OR m.fed_rate IS NULL)
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.WARN)
    return _result(count, df, AssetCheckSeverity.WARN)


@asset_check(asset="bq_macro_economic_daily", name="no_large_date_gaps")
def check_macro_no_large_date_gaps() -> AssetCheckResult:
    # IDX closes for Lebaran (Eid) for 5–7 consecutive trading days.
    # Combined with surrounding weekends this can reach 14 calendar days,
    # so the threshold is set to 14 to avoid false positives on long holidays.
    # A gap > 14 days indicates a likely extract failure or API outage.
    sql = f"""
        WITH consecutive AS (
            SELECT
                date,
                LEAD(date) OVER (ORDER BY date) AS next_date
            FROM {_tbl('macro_economic_daily')}
        )
        SELECT date, next_date,
               DATE_DIFF(DATE(next_date), DATE(date), DAY) AS gap_days
        FROM consecutive
        WHERE next_date IS NOT NULL
          AND DATE_DIFF(DATE(next_date), DATE(date), DAY) > 14
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.WARN)
    return _result(count, df, AssetCheckSeverity.WARN)


# ---------------------------------------------------------------------------
# bq_stock_signals — technical-signal snapshot checks
# ---------------------------------------------------------------------------

@asset_check(asset="bq_stock_signals", name="rsi_in_range", blocking=True)
def check_signals_rsi_in_range() -> AssetCheckResult:
    # RSI is bounded [0, 100] by definition — anything outside means a
    # computation error in the indicator pipeline.
    sql = f"""
        SELECT date, ticker, rsi14
        FROM {_tbl('stock_signals')}
        WHERE rsi14 < 0 OR rsi14 > 100
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.ERROR)
    return _result(count, df, AssetCheckSeverity.ERROR)


@asset_check(asset="bq_stock_signals", name="signal_in_valid_set", blocking=True)
def check_signals_valid_label() -> AssetCheckResult:
    # The screener relies on these exact labels; an unexpected value means the
    # classification produced something the UI can't render.
    sql = f"""
        SELECT date, ticker, signal
        FROM {_tbl('stock_signals')}
        WHERE signal NOT IN ('BUY', 'HOLD', 'SELL', 'OVERBOUGHT')
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.ERROR)
    return _result(count, df, AssetCheckSeverity.ERROR)


@asset_check(asset="bq_stock_signals", name="ticker_coverage", blocking=False)
def check_signals_ticker_coverage() -> AssetCheckResult:
    # The snapshot holds exactly one row per tracked stock. Fewer means a
    # ticker dropped out of the upstream price history; more means a duplicate.
    expected = expected_stock_count()
    sql = f"""
        SELECT row_count
        FROM (SELECT COUNT(*) AS row_count FROM {_tbl('stock_signals')})
        WHERE row_count != {expected}
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.WARN)
    return _result(count, df, AssetCheckSeverity.WARN)


# ---------------------------------------------------------------------------
# bq_news_sentiment / bq_daily_briefing — AI layer checks
# ---------------------------------------------------------------------------

@asset_check(asset="bq_news_sentiment", name="sentiment_label_valid", blocking=True)
def check_news_sentiment_label_valid() -> AssetCheckResult:
    # Every scored article must carry one of the three known labels; an unknown
    # value means scoring/parsing produced something the UI can't map.
    sql = f"""
        SELECT url, sentiment_label
        FROM {_tbl('news_articles')}
        WHERE sentiment_label IS NOT NULL
          AND sentiment_label NOT IN ('positif', 'negatif', 'netral')
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.ERROR)
    return _result(count, df, AssetCheckSeverity.ERROR)


@asset_check(asset="bq_daily_briefing", name="briefing_not_empty", blocking=True)
def check_briefing_not_empty() -> AssetCheckResult:
    # The briefing is the dashboard hero — a null/empty narrative is a failure.
    sql = f"""
        SELECT date, narrative
        FROM {_tbl('daily_briefing')}
        WHERE narrative IS NULL OR TRIM(narrative) = ''
    """
    try:
        client = bigquery.Client(project=_PROJECT)
        count, df = _query_violations(client, sql)
    except NotFound:
        return _table_missing(AssetCheckSeverity.ERROR)
    return _result(count, df, AssetCheckSeverity.ERROR)
