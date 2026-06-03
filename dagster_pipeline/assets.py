"""
dagster_pipeline/assets.py
--------------------------
Defines all Dagster Software-Defined Assets (SDAs) for the finance ETL pipeline.

Asset dependency graph:
                        ┌─► raw_ihsg_gcs
    extract_ihsg ───────┤
                        └─► transformed_data ─► bq_macro_economic_daily
                        ┌─► raw_fred_gcs      │
    extract_fred ───────┤                     │
                        └─► transformed_data ─┘
                        ┌─► raw_currency_gcs
    extract_currency ───┤
                        ├─► transformed_data
                        └─► bq_currency_rates   (direct — own table)

    extract_ihsg ──────────► bq_stock_performance

Groups:
    extract   — raw data pulled from external sources
    raw_gcs   — bronze layer: raw Parquet files in GCS
    transform — silver/gold layer: joined, cleaned DataFrame
    bigquery  — gold layer: BigQuery tables

Holiday behaviour:
    On non-trading days (public holidays, weekends caught by manual runs),
    extract assets return empty DataFrames instead of raising Failure.
    Every downstream asset guards against empty inputs and returns a
    MaterializeResult with skipped=True rather than attempting a no-op
    GCS upload or BigQuery merge.
"""

import io
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from dagster import (
    AssetExecutionContext,
    Backoff,
    Config,
    Failure,
    MaterializeResult,
    MetadataValue,
    RetryPolicy,
    asset,
)
from dotenv import load_dotenv
from google.cloud import bigquery
from requests.exceptions import RequestException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from ai.briefing import build_briefing
from ai.sentiment import score_headlines
from config.universe import index_membership_map, name_map
from extract.currency_data import extract_currency as _extract_currency
from extract.fred_data import extract_fred as _extract_fred
from extract.ihsg_data import extract_ihsg as _extract_ihsg
from extract.news_data import extract_news as _extract_news
from load.bigquery_loader import load_to_bigquery
from load.gcs_loader import upload_to_gcs
from transform.data_transform import transform_data
from transform.indicators import compute_signal_snapshot

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
BQ_DATASET     = os.environ.get("BQ_DATASET", "")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_EXTRACT_RETRY = RetryPolicy(max_retries=3, delay=60, backoff=Backoff.EXPONENTIAL)


def _date_range(df: pd.DataFrame) -> str:
    return f"{df['date'].min()} → {df['date'].max()}"


def _preview_md(df: pd.DataFrame, n: int = 5) -> str:
    sample = df.head(n)
    cols   = list(sample.columns)
    header = "| " + " | ".join(cols) + " |"
    sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows   = [
        "| " + " | ".join(str(v) for v in row) + " |"
        for _, row in sample.iterrows()
    ]
    return "\n".join([header, sep, *rows])


def _parquet_size_mb(df: pd.DataFrame) -> float:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    return round(buf.tell() / (1024 ** 2), 3)


# ---------------------------------------------------------------------------
# Shared configuration
# ---------------------------------------------------------------------------

class DateRangeConfig(Config):
    """
    Configurable date window for extract assets.

    Defaults to a 2-year lookback (suitable for initial / backfill runs).
    The weekday schedule overrides these with a 2-day window.
    """
    start_date: str = (datetime.today() - timedelta(days=730)).strftime("%Y-%m-%d")
    end_date:   str = datetime.today().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# EXTRACT assets
# ---------------------------------------------------------------------------

@asset(
    group_name="extract",
    description="Extract IHSG index (^JKSE) and IDX stocks from Yahoo Finance.",
    retry_policy=_EXTRACT_RETRY,
)
def extract_ihsg(
    context: AssetExecutionContext,
    config: DateRangeConfig,
) -> pd.DataFrame:
    t0 = time.perf_counter()
    context.log.info(
        f"[extract_ihsg] Starting extract: {config.start_date} → {config.end_date}"
    )

    try:
        df = _extract_ihsg(start_date=config.start_date, end_date=config.end_date)
    except RequestException as exc:
        raise Failure(
            description=f"Network error fetching IHSG data: {exc}",
            metadata={"error": MetadataValue.text(str(exc))},
        ) from exc

    duration = time.perf_counter() - t0

    if df.empty:
        context.log.warning(
            f"[extract_ihsg] No market data for {config.start_date} → {config.end_date} "
            "(holiday or non-trading period). Downstream assets will be skipped."
        )
        context.add_output_metadata({
            "skipped":    MetadataValue.bool(True),
            "reason":     MetadataValue.text("no trading data — holiday or non-trading period"),
            "row_count":  MetadataValue.int(0),
        })
        context.log.info(f"[extract_ihsg] Done (no data) in {duration:.1f}s")
        return df

    tickers = sorted(df["ticker"].unique().tolist())
    context.log.info(
        f"[extract_ihsg] Extracted {len(df)} rows across {len(tickers)} tickers: {tickers}"
    )

    context.add_output_metadata({
        "row_count":  MetadataValue.int(len(df)),
        "date_range": MetadataValue.text(_date_range(df)),
        "tickers":    MetadataValue.text(", ".join(tickers)),
        "preview":    MetadataValue.md(_preview_md(df)),
    })

    context.log.info(f"[extract_ihsg] Done — {len(df)} rows in {duration:.1f}s")
    return df


@asset(
    group_name="extract",
    description="Extract CPIAUCSL, FEDFUNDS, and DEXINUS from the FRED API.",
    retry_policy=_EXTRACT_RETRY,
)
def extract_fred(
    context: AssetExecutionContext,
    config: DateRangeConfig,
) -> pd.DataFrame:
    t0 = time.perf_counter()
    context.log.info(
        f"[extract_fred] Starting extract: {config.start_date} → {config.end_date}"
    )

    try:
        df = _extract_fred(start_date=config.start_date, end_date=config.end_date)
    except RequestException as exc:
        raise Failure(
            description=f"Network error fetching FRED data: {exc}",
            metadata={"error": MetadataValue.text(str(exc))},
        ) from exc

    duration = time.perf_counter() - t0

    if df.empty:
        # FRED series are monthly; a short lookback window may contain no new observations.
        context.log.warning(
            f"[extract_fred] No FRED observations for {config.start_date} → {config.end_date} "
            "(short window with no new monthly data points)."
        )
        context.add_output_metadata({
            "skipped":   MetadataValue.bool(True),
            "reason":    MetadataValue.text("no new FRED observations in this window"),
            "row_count": MetadataValue.int(0),
        })
        context.log.info(f"[extract_fred] Done (no data) in {duration:.1f}s")
        return df

    context.log.info(f"[extract_fred] Extracted {len(df)} rows")

    context.add_output_metadata({
        "row_count":  MetadataValue.int(len(df)),
        "date_range": MetadataValue.text(_date_range(df)),
        "preview":    MetadataValue.md(_preview_md(df)),
    })

    context.log.info(f"[extract_fred] Done — {len(df)} rows in {duration:.1f}s")
    return df


@asset(
    group_name="extract",
    description="Extract IDR/USD, EUR/IDR, JPY/IDR exchange rates from Yahoo Finance.",
    retry_policy=_EXTRACT_RETRY,
)
def extract_currency(
    context: AssetExecutionContext,
    config: DateRangeConfig,
) -> pd.DataFrame:
    t0 = time.perf_counter()
    context.log.info(
        f"[extract_currency] Starting extract: {config.start_date} → {config.end_date}"
    )

    try:
        df = _extract_currency(start_date=config.start_date, end_date=config.end_date)
    except RequestException as exc:
        raise Failure(
            description=f"Network error fetching currency data: {exc}",
            metadata={"error": MetadataValue.text(str(exc))},
        ) from exc

    duration = time.perf_counter() - t0

    if df.empty:
        context.log.warning(
            f"[extract_currency] No currency data for {config.start_date} → {config.end_date}."
        )
        context.add_output_metadata({
            "skipped":   MetadataValue.bool(True),
            "reason":    MetadataValue.text("no currency data returned"),
            "row_count": MetadataValue.int(0),
        })
        context.log.info(f"[extract_currency] Done (no data) in {duration:.1f}s")
        return df

    context.log.info(f"[extract_currency] Extracted {len(df)} rows")

    context.add_output_metadata({
        "row_count":  MetadataValue.int(len(df)),
        "date_range": MetadataValue.text(_date_range(df)),
        "preview":    MetadataValue.md(_preview_md(df)),
    })

    context.log.info(f"[extract_currency] Done — {len(df)} rows in {duration:.1f}s")
    return df


@asset(
    group_name="extract",
    description="Extract global news articles relevant to IHSG from NewsAPI.",
    retry_policy=_EXTRACT_RETRY,
)
def extract_news(
    context: AssetExecutionContext,
    config: DateRangeConfig,
) -> pd.DataFrame:
    t0 = time.perf_counter()
    context.log.info(
        f"[extract_news] Starting extract: {config.start_date} → {config.end_date}"
    )

    try:
        df = _extract_news(start_date=config.start_date, end_date=config.end_date)
    except RequestException as exc:
        raise Failure(
            description=f"Network error fetching news data: {exc}",
            metadata={"error": MetadataValue.text(str(exc))},
        ) from exc

    duration = time.perf_counter() - t0

    if df.empty:
        context.log.warning(
            f"[extract_news] No articles returned for {config.start_date} → {config.end_date}."
        )
        context.add_output_metadata({
            "skipped":   MetadataValue.bool(True),
            "reason":    MetadataValue.text("no articles returned"),
            "row_count": MetadataValue.int(0),
        })
        context.log.info(f"[extract_news] Done (no data) in {duration:.1f}s")
        return df

    sources = sorted(df["source"].dropna().unique().tolist())[:10]
    context.log.info(
        f"[extract_news] Extracted {len(df)} articles from sources: {sources}"
    )

    context.add_output_metadata({
        "row_count":  MetadataValue.int(len(df)),
        "date_range": MetadataValue.text(_date_range(df)),
        "sources":    MetadataValue.text(", ".join(sources)),
        "preview":    MetadataValue.md(_preview_md(df)),
    })

    context.log.info(f"[extract_news] Done — {len(df)} articles in {duration:.1f}s")
    return df


# ---------------------------------------------------------------------------
# RAW GCS assets  (bronze layer)
# ---------------------------------------------------------------------------

@asset(
    group_name="raw_gcs",
    description="Upload raw IHSG DataFrame to GCS as Parquet (bronze layer).",
)
def raw_ihsg_gcs(
    context: AssetExecutionContext,
    extract_ihsg: pd.DataFrame,
) -> MaterializeResult:
    if extract_ihsg.empty:
        context.log.warning("[raw_ihsg_gcs] No IHSG data — skipping GCS upload.")
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    t0 = time.perf_counter()
    context.log.info(f"[raw_ihsg_gcs] Serialising {len(extract_ihsg)} rows to Parquet")

    file_size_mb = _parquet_size_mb(extract_ihsg)
    context.log.info(f"[raw_ihsg_gcs] Parquet size: {file_size_mb} MB — uploading to GCS")

    gcs_path = upload_to_gcs(extract_ihsg, folder="ihsg")

    duration = time.perf_counter() - t0
    context.log.info(f"[raw_ihsg_gcs] Uploaded → {gcs_path} in {duration:.1f}s")

    return MaterializeResult(
        metadata={
            "gcs_path":     MetadataValue.text(gcs_path),
            "row_count":    MetadataValue.int(len(extract_ihsg)),
            "date_range":   MetadataValue.text(_date_range(extract_ihsg)),
            "file_size_mb": MetadataValue.float(file_size_mb),
        }
    )


@asset(
    group_name="raw_gcs",
    description="Upload raw FRED DataFrame to GCS as Parquet (bronze layer).",
)
def raw_fred_gcs(
    context: AssetExecutionContext,
    extract_fred: pd.DataFrame,
) -> MaterializeResult:
    if extract_fred.empty:
        context.log.warning("[raw_fred_gcs] No FRED data — skipping GCS upload.")
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    t0 = time.perf_counter()
    context.log.info(f"[raw_fred_gcs] Serialising {len(extract_fred)} rows to Parquet")

    file_size_mb = _parquet_size_mb(extract_fred)
    context.log.info(f"[raw_fred_gcs] Parquet size: {file_size_mb} MB — uploading to GCS")

    gcs_path = upload_to_gcs(extract_fred, folder="fred")

    duration = time.perf_counter() - t0
    context.log.info(f"[raw_fred_gcs] Uploaded → {gcs_path} in {duration:.1f}s")

    return MaterializeResult(
        metadata={
            "gcs_path":     MetadataValue.text(gcs_path),
            "row_count":    MetadataValue.int(len(extract_fred)),
            "date_range":   MetadataValue.text(_date_range(extract_fred)),
            "file_size_mb": MetadataValue.float(file_size_mb),
        }
    )


@asset(
    group_name="raw_gcs",
    description="Upload raw currency DataFrame to GCS as Parquet (bronze layer).",
)
def raw_currency_gcs(
    context: AssetExecutionContext,
    extract_currency: pd.DataFrame,
) -> MaterializeResult:
    if extract_currency.empty:
        context.log.warning("[raw_currency_gcs] No currency data — skipping GCS upload.")
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    t0 = time.perf_counter()
    context.log.info(f"[raw_currency_gcs] Serialising {len(extract_currency)} rows to Parquet")

    file_size_mb = _parquet_size_mb(extract_currency)
    context.log.info(f"[raw_currency_gcs] Parquet size: {file_size_mb} MB — uploading to GCS")

    gcs_path = upload_to_gcs(extract_currency, folder="currency")

    duration = time.perf_counter() - t0
    context.log.info(f"[raw_currency_gcs] Uploaded → {gcs_path} in {duration:.1f}s")

    return MaterializeResult(
        metadata={
            "gcs_path":     MetadataValue.text(gcs_path),
            "row_count":    MetadataValue.int(len(extract_currency)),
            "date_range":   MetadataValue.text(_date_range(extract_currency)),
            "file_size_mb": MetadataValue.float(file_size_mb),
        }
    )


@asset(
    group_name="raw_gcs",
    description="Upload raw news articles DataFrame to GCS as Parquet (bronze layer).",
)
def raw_news_gcs(
    context: AssetExecutionContext,
    extract_news: pd.DataFrame,
) -> MaterializeResult:
    if extract_news.empty:
        context.log.warning("[raw_news_gcs] No news data — skipping GCS upload.")
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    t0 = time.perf_counter()
    context.log.info(f"[raw_news_gcs] Serialising {len(extract_news)} articles to Parquet")

    file_size_mb = _parquet_size_mb(extract_news)
    context.log.info(f"[raw_news_gcs] Parquet size: {file_size_mb} MB — uploading to GCS")

    gcs_path = upload_to_gcs(extract_news, folder="news")

    duration = time.perf_counter() - t0
    context.log.info(f"[raw_news_gcs] Uploaded → {gcs_path} in {duration:.1f}s")

    return MaterializeResult(
        metadata={
            "gcs_path":     MetadataValue.text(gcs_path),
            "row_count":    MetadataValue.int(len(extract_news)),
            "date_range":   MetadataValue.text(_date_range(extract_news)),
            "file_size_mb": MetadataValue.float(file_size_mb),
        }
    )


# ---------------------------------------------------------------------------
# TRANSFORM asset  (gold layer)
# ---------------------------------------------------------------------------

@asset(
    group_name="transform",
    description=(
        "Join IHSG, FRED, and currency data on date. "
        "Forward-fill monthly FRED values, add derived columns, "
        "and drop incomplete rows."
    ),
)
def transformed_data(
    context: AssetExecutionContext,
    extract_ihsg: pd.DataFrame,
    extract_fred: pd.DataFrame,
    extract_currency: pd.DataFrame,
) -> pd.DataFrame:
    # ^JKSE is the join base — no IHSG data means nothing to transform.
    if extract_ihsg.empty:
        context.log.warning(
            "[transformed_data] IHSG data is empty (holiday/non-trading day) — skipping transform."
        )
        context.add_output_metadata({
            "skipped":   MetadataValue.bool(True),
            "reason":    MetadataValue.text("no IHSG data"),
            "row_count": MetadataValue.int(0),
        })
        return pd.DataFrame()

    t0 = time.perf_counter()
    context.log.info(
        f"[transformed_data] Joining IHSG ({len(extract_ihsg)} rows), "
        f"FRED ({len(extract_fred)} rows), "
        f"currency ({len(extract_currency)} rows)"
    )

    df = transform_data(extract_ihsg, extract_fred, extract_currency)

    context.log.info(
        f"[transformed_data] Transform complete — {len(df)} rows, "
        f"columns: {list(df.columns)}"
    )

    context.add_output_metadata({
        "row_count":  MetadataValue.int(len(df)),
        "date_range": MetadataValue.text(_date_range(df)),
        "columns":    MetadataValue.text(", ".join(df.columns.tolist())),
        "preview":    MetadataValue.md(_preview_md(df)),
    })

    duration = time.perf_counter() - t0
    context.log.info(f"[transformed_data] Done — {len(df)} rows in {duration:.1f}s")
    return df


# ---------------------------------------------------------------------------
# BIGQUERY assets  (gold layer)
# ---------------------------------------------------------------------------

@asset(
    group_name="bigquery",
    description="Load combined macro-economic daily data into BigQuery.",
)
def bq_macro_economic_daily(
    context: AssetExecutionContext,
    transformed_data: pd.DataFrame,
) -> MaterializeResult:
    if transformed_data.empty:
        context.log.warning(
            "[bq_macro_economic_daily] No transformed data — skipping BigQuery merge."
        )
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.macro_economic_daily"
    t0 = time.perf_counter()
    context.log.info(
        f"[bq_macro_economic_daily] Merging {len(transformed_data)} rows → {table_id}"
    )

    stats = load_to_bigquery(
        transformed_data,
        table_name="macro_economic_daily",
        mode="merge",
        merge_keys=["date"],
    )

    # ihsg_return_pct is not in the transformed DataFrame — compute it here
    # using LAG() over the full table so every incremental run produces
    # correct values instead of NaN for the first day of each batch window.
    context.log.info("[bq_macro_economic_daily] Recalculating ihsg_return_pct via BigQuery LAG()")
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    bq_client.query(f"""
        UPDATE `{table_id}` t
        SET ihsg_return_pct = sub.return_pct
        FROM (
            SELECT
                date,
                SAFE_DIVIDE(
                    ihsg_close - LAG(ihsg_close) OVER (ORDER BY date),
                    LAG(ihsg_close) OVER (ORDER BY date)
                ) * 100 AS return_pct
            FROM `{table_id}`
        ) sub
        WHERE t.date = sub.date
    """).result()
    context.log.info("[bq_macro_economic_daily] ihsg_return_pct recalculation complete")

    total_bytes_mb = (
        round((stats["total_bytes"] or 0) / (1024 ** 2), 2)
        if stats else 0
    )

    duration = time.perf_counter() - t0
    context.log.info(
        f"[bq_macro_economic_daily] Done — "
        f"{stats['total_rows']:,} total rows, "
        f"{total_bytes_mb} MB in {duration:.1f}s"
    )

    return MaterializeResult(
        metadata={
            "table_id":        MetadataValue.text(table_id),
            "row_count":       MetadataValue.int(len(transformed_data)),
            "date_range":      MetadataValue.text(_date_range(transformed_data)),
            "bytes_processed": MetadataValue.text(f"{total_bytes_mb} MB (table total)"),
            "preview":         MetadataValue.md(_preview_md(transformed_data)),
        }
    )


@asset(
    group_name="bigquery",
    description="Load global news articles into BigQuery.",
)
def bq_news_articles(
    context: AssetExecutionContext,
    extract_news: pd.DataFrame,
) -> MaterializeResult:
    if extract_news.empty:
        context.log.warning("[bq_news_articles] No news data — skipping BigQuery merge.")
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.news_articles"
    t0 = time.perf_counter()
    context.log.info(
        f"[bq_news_articles] Merging {len(extract_news)} articles → {table_id}"
    )

    stats = load_to_bigquery(
        extract_news,
        table_name="news_articles",
        mode="merge",
        merge_keys=["url"],
    )

    total_bytes_mb = (
        round((stats["total_bytes"] or 0) / (1024 ** 2), 2)
        if stats else 0
    )

    duration = time.perf_counter() - t0
    context.log.info(
        f"[bq_news_articles] Done — "
        f"{stats['total_rows']:,} total rows, "
        f"{total_bytes_mb} MB in {duration:.1f}s"
    )

    return MaterializeResult(
        metadata={
            "table_id":        MetadataValue.text(table_id),
            "row_count":       MetadataValue.int(len(extract_news)),
            "date_range":      MetadataValue.text(_date_range(extract_news)),
            "bytes_processed": MetadataValue.text(f"{total_bytes_mb} MB (table total)"),
            "preview":         MetadataValue.md(_preview_md(extract_news)),
        }
    )


@asset(
    group_name="bigquery",
    description=(
        "Load daily currency rates (USD/IDR, EUR/IDR, JPY/IDR) directly into "
        "BigQuery as a standalone table. Independent of the IHSG trading calendar."
    ),
)
def bq_currency_rates(
    context: AssetExecutionContext,
    extract_currency: pd.DataFrame,
) -> MaterializeResult:
    if extract_currency.empty:
        context.log.warning("[bq_currency_rates] No currency data — skipping BigQuery merge.")
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.currency_rates"
    t0 = time.perf_counter()
    context.log.info(
        f"[bq_currency_rates] Merging {len(extract_currency)} rows → {table_id}"
    )

    stats = load_to_bigquery(
        extract_currency,
        table_name="currency_rates",
        mode="merge",
        merge_keys=["date"],
    )

    total_bytes_mb = (
        round((stats["total_bytes"] or 0) / (1024 ** 2), 2)
        if stats else 0
    )

    duration = time.perf_counter() - t0
    context.log.info(
        f"[bq_currency_rates] Done — "
        f"{stats['total_rows']:,} total rows, "
        f"{total_bytes_mb} MB in {duration:.1f}s"
    )

    return MaterializeResult(
        metadata={
            "table_id":        MetadataValue.text(table_id),
            "row_count":       MetadataValue.int(len(extract_currency)),
            "date_range":      MetadataValue.text(_date_range(extract_currency)),
            "bytes_processed": MetadataValue.text(f"{total_bytes_mb} MB (table total)"),
            "preview":         MetadataValue.md(_preview_md(extract_currency)),
        }
    )


@asset(
    group_name="bigquery",
    description=(
        "Load individual IDX stock performance data into BigQuery. "
        "Excludes the ^JKSE index row — individual tickers only."
    ),
)
def bq_stock_performance(
    context: AssetExecutionContext,
    extract_ihsg: pd.DataFrame,
) -> MaterializeResult:
    if extract_ihsg.empty:
        context.log.warning(
            "[bq_stock_performance] No IHSG data (holiday/non-trading day) — skipping BigQuery merge."
        )
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.stock_performance"

    stock_df = extract_ihsg[extract_ihsg["ticker"] != "^JKSE"].copy()
    stock_df["date"]  = pd.to_datetime(stock_df["date"])
    stock_df["year"]  = stock_df["date"].dt.year
    stock_df["month"] = stock_df["date"].dt.month
    stock_df["date"]  = stock_df["date"].dt.strftime("%Y-%m-%d")

    tickers = sorted(stock_df["ticker"].unique().tolist())
    t0 = time.perf_counter()
    context.log.info(
        f"[bq_stock_performance] Merging {len(stock_df)} rows "
        f"({tickers}) → {table_id}"
    )

    stats = load_to_bigquery(
        stock_df,
        table_name="stock_performance",
        mode="merge",
        merge_keys=["date", "ticker"],
    )

    total_bytes_mb = (
        round((stats["total_bytes"] or 0) / (1024 ** 2), 2)
        if stats else 0
    )

    duration = time.perf_counter() - t0
    context.log.info(
        f"[bq_stock_performance] Done — "
        f"{stats['total_rows']:,} total rows, "
        f"{total_bytes_mb} MB in {duration:.1f}s"
    )

    return MaterializeResult(
        metadata={
            "table_id":        MetadataValue.text(table_id),
            "row_count":       MetadataValue.int(len(stock_df)),
            "date_range":      MetadataValue.text(_date_range(stock_df)),
            "tickers":         MetadataValue.text(", ".join(tickers)),
            "bytes_processed": MetadataValue.text(f"{total_bytes_mb} MB (table total)"),
            "preview":         MetadataValue.md(_preview_md(stock_df)),
        }
    )


@asset(
    group_name="bigquery",
    deps=[bq_stock_performance],
    description=(
        "Compute technical indicators (MA20/50/200, Wilder RSI, 20-day momentum, "
        "52-week high/low) and a transparent BUY/HOLD/SELL/OVERBOUGHT signal per "
        "ticker from stock_performance, writing the latest snapshot (one row per "
        "ticker) to the stock_signals table that powers the screener."
    ),
)
def bq_stock_signals(context: AssetExecutionContext) -> MaterializeResult:
    source_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.stock_performance"
    table_id  = f"{GCP_PROJECT_ID}.{BQ_DATASET}.stock_signals"

    # Read the full price history (indicators like MA200 need the long window),
    # not just the latest batch — so we query the warehouse rather than take an
    # in-memory input from bq_stock_performance.
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    history = bq_client.query(
        f"SELECT date, ticker, close, volume FROM `{source_id}`"
    ).to_dataframe()

    if history.empty:
        context.log.warning("[bq_stock_signals] stock_performance is empty — skipping.")
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})

    t0 = time.perf_counter()
    context.log.info(
        f"[bq_stock_signals] Computing indicators over {len(history)} rows "
        f"({history['ticker'].nunique()} tickers)"
    )

    snapshot = compute_signal_snapshot(history)

    # Enrich with display name + index tags (the latter drives the universe filter).
    names   = name_map()
    indices = index_membership_map()
    snapshot["name"]             = snapshot["ticker"].map(names)
    snapshot["index_membership"] = snapshot["ticker"].map(indices)

    columns = [
        "date", "ticker", "name", "index_membership",
        "close", "return_1d", "volume", "vol_avg20",
        "ma20", "ma50", "ma200", "ma_trend",
        "rsi14", "momentum_20d", "high_52w", "low_52w",
        "signal",
    ]
    signals = snapshot[columns].copy()

    stats = load_to_bigquery(signals, table_name="stock_signals", mode="truncate")

    total_bytes_mb = (
        round((stats["total_bytes"] or 0) / (1024 ** 2), 2) if stats else 0
    )
    duration = time.perf_counter() - t0
    dist = signals["signal"].value_counts().to_dict()
    context.log.info(
        f"[bq_stock_signals] Done — {len(signals)} tickers, signals={dist} "
        f"in {duration:.1f}s"
    )

    return MaterializeResult(
        metadata={
            "table_id":      MetadataValue.text(table_id),
            "row_count":     MetadataValue.int(len(signals)),
            "as_of":         MetadataValue.text(str(signals["date"].max())),
            "signal_counts": MetadataValue.text(", ".join(f"{k}: {v}" for k, v in dist.items())),
            "table_bytes":   MetadataValue.text(f"{total_bytes_mb} MB (table total)"),
            "preview":       MetadataValue.md(_preview_md(signals)),
        }
    )


@asset(
    group_name="bigquery",
    deps=[bq_news_articles],
    description=(
        "Score the sentiment of news headlines via the LLM (batched, JSON mode) "
        "and write sentiment_label / sentiment_score back onto news_articles. "
        "Only scores rows not yet scored — cheap & idempotent across daily runs."
    ),
)
def bq_news_sentiment(context: AssetExecutionContext) -> MaterializeResult:
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.news_articles"
    client = bigquery.Client(project=GCP_PROJECT_ID)

    # Ensure the sentiment columns exist (no-op after the first run).
    client.query(f"""
        ALTER TABLE `{table_id}`
        ADD COLUMN IF NOT EXISTS sentiment_label STRING,
        ADD COLUMN IF NOT EXISTS sentiment_score FLOAT64
    """).result()

    todo = [
        {"url": r["url"], "title": r["title"]}
        for r in client.query(
            f"SELECT url, title FROM `{table_id}` WHERE sentiment_label IS NULL"
        ).result()
    ]
    if not todo:
        context.log.info("[bq_news_sentiment] All articles already scored — nothing to do.")
        return MaterializeResult(metadata={"scored": MetadataValue.int(0), "skipped": MetadataValue.bool(True)})

    t0 = time.perf_counter()
    context.log.info(f"[bq_news_sentiment] Scoring {len(todo)} unscored articles via LLM...")
    scored = pd.DataFrame(score_headlines(todo))  # url, sentiment_label, sentiment_score

    # Write sentiment back via a staging table + MERGE UPDATE on url.
    staging_id = f"{table_id}_sentiment_staging"
    client.load_table_from_dataframe(
        scored, staging_id,
        job_config=bigquery.LoadJobConfig(
            autodetect=True, write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        ),
    ).result()
    try:
        client.query(f"""
            MERGE `{table_id}` t
            USING `{staging_id}` s ON t.url = s.url
            WHEN MATCHED THEN UPDATE SET
                t.sentiment_label = s.sentiment_label,
                t.sentiment_score = s.sentiment_score
        """).result()
    finally:
        client.delete_table(staging_id, not_found_ok=True)

    dist = scored["sentiment_label"].value_counts().to_dict()
    mood = round(float(scored["sentiment_score"].mean()), 3)
    duration = time.perf_counter() - t0
    context.log.info(
        f"[bq_news_sentiment] Done — scored {len(scored)}, dist={dist}, "
        f"batch_mood={mood} in {duration:.1f}s"
    )
    return MaterializeResult(
        metadata={
            "scored":       MetadataValue.int(len(scored)),
            "distribution": MetadataValue.text(", ".join(f"{k}: {v}" for k, v in dist.items())),
            "batch_mood":   MetadataValue.float(mood),
            "preview":      MetadataValue.md(_preview_md(scored)),
        }
    )


@asset(
    group_name="bigquery",
    deps=[bq_macro_economic_daily, bq_stock_signals, bq_news_sentiment],
    description=(
        "Generate the daily AI market briefing — a plain-Indonesian narrative of "
        "why the market moved — from the macro snapshot, stock breadth/movers, and "
        "scored news sentiment, and store it in the daily_briefing table."
    ),
)
def bq_daily_briefing(context: AssetExecutionContext) -> MaterializeResult:
    client = bigquery.Client(project=GCP_PROJECT_ID)

    def _tbl(name: str) -> str:
        return f"`{GCP_PROJECT_ID}.{BQ_DATASET}.{name}`"

    macro = list(client.query(f"""
        SELECT CAST(date AS STRING) AS date, ihsg_close, ihsg_return_pct, usd_idr
        FROM {_tbl('macro_economic_daily')}
        ORDER BY date DESC LIMIT 1
    """).result())
    if not macro:
        context.log.warning("[bq_daily_briefing] No macro data — skipping.")
        return MaterializeResult(metadata={"skipped": MetadataValue.bool(True)})
    m = macro[0]

    breadth = list(client.query(f"""
        SELECT COUNTIF(return_1d > 0) AS adv, COUNTIF(return_1d < 0) AS dec
        FROM {_tbl('stock_signals')}
    """).result())[0]
    movers = [
        {"ticker": r["ticker"], "return_pct": r["return_pct"]}
        for r in client.query(f"""
            SELECT ticker, ROUND(return_1d, 2) AS return_pct
            FROM {_tbl('stock_signals')} ORDER BY return_1d DESC
        """).result()
    ]
    news = list(client.query(f"""
        SELECT ROUND(AVG(sentiment_score), 3) AS mood,
               COUNTIF(sentiment_label = 'positif') AS pos,
               COUNTIF(sentiment_label = 'negatif') AS neg,
               COUNTIF(sentiment_label = 'netral')  AS neu
        FROM {_tbl('news_articles')} WHERE sentiment_label IS NOT NULL
    """).result())[0]
    headlines = [
        {"title": r["title"], "sentiment_label": r["sentiment_label"]}
        for r in client.query(f"""
            SELECT title, sentiment_label FROM {_tbl('news_articles')}
            WHERE sentiment_label IS NOT NULL ORDER BY published_at DESC LIMIT 6
        """).result()
    ]

    ctx = {
        "date": m["date"], "ihsg_close": m["ihsg_close"],
        "ihsg_return_pct": m["ihsg_return_pct"], "usd_idr": m["usd_idr"],
        "universe": "LQ45",
        "advancers": breadth["adv"], "decliners": breadth["dec"],
        "top_gainers": movers[:3], "top_losers": movers[-3:][::-1],
        "news_mood": news["mood"], "pos": news["pos"], "neg": news["neg"], "neu": news["neu"],
        "top_headlines": headlines,
    }

    t0 = time.perf_counter()
    context.log.info(f"[bq_daily_briefing] Generating briefing for {m['date']} via LLM...")
    narrative = build_briefing(ctx)

    mood = float(news["mood"]) if news["mood"] is not None else 0.0
    df = pd.DataFrame([{
        "date": m["date"],
        "narrative": narrative,
        "ihsg_return_pct": m["ihsg_return_pct"],
        "news_mood": mood,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }])
    load_to_bigquery(df, table_name="daily_briefing", mode="merge", merge_keys=["date"])

    duration = time.perf_counter() - t0
    context.log.info(f"[bq_daily_briefing] Done — {len(narrative)} chars for {m['date']} in {duration:.1f}s")
    return MaterializeResult(
        metadata={
            "date":      MetadataValue.text(m["date"]),
            "news_mood": MetadataValue.float(mood),
            "chars":     MetadataValue.int(len(narrative)),
            "briefing":  MetadataValue.md(narrative),
        }
    )
