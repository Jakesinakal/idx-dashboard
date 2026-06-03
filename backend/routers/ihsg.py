from fastapi import APIRouter, HTTPException, Query
from google.cloud import bigquery

from database import TABLE_PREFIX, get_client

router = APIRouter()


@router.get("/ihsg/history")
def get_ihsg_history(
    days: int = Query(90, ge=7, le=730, description="Lookback window in days"),
):
    """IHSG close series for the last N days (relative to the latest data point)."""
    client = get_client()
    query = f"""
        SELECT CAST(date AS STRING) AS date, ihsg_close
        FROM {TABLE_PREFIX}.macro_economic_daily
        WHERE ihsg_close IS NOT NULL
          AND CAST(date AS DATE) >= DATE_SUB(
              (SELECT CAST(MAX(date) AS DATE) FROM {TABLE_PREFIX}.macro_economic_daily),
              INTERVAL @days DAY
          )
        ORDER BY date ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("days", "INT64", days)]
    )
    rows = list(client.query(query, job_config=job_config).result())
    if not rows:
        raise HTTPException(status_code=404, detail="No IHSG history available")
    return [{"date": r["date"], "ihsg_close": r["ihsg_close"]} for r in rows]


@router.get("/ihsg/comparison")
def get_ihsg_comparison():
    client = get_client()
    query = f"""
        WITH latest AS (
            SELECT date, ihsg_close
            FROM {TABLE_PREFIX}.macro_economic_daily
            ORDER BY date DESC
            LIMIT 1
        ),
        d30 AS (
            SELECT date, ihsg_close
            FROM {TABLE_PREFIX}.macro_economic_daily
            WHERE CAST(date AS DATE) <= DATE_SUB(CAST((SELECT date FROM latest) AS DATE), INTERVAL 30 DAY)
            ORDER BY date DESC
            LIMIT 1
        ),
        d60 AS (
            SELECT date, ihsg_close
            FROM {TABLE_PREFIX}.macro_economic_daily
            WHERE CAST(date AS DATE) <= DATE_SUB(CAST((SELECT date FROM latest) AS DATE), INTERVAL 60 DAY)
            ORDER BY date DESC
            LIMIT 1
        ),
        d90 AS (
            SELECT date, ihsg_close
            FROM {TABLE_PREFIX}.macro_economic_daily
            WHERE CAST(date AS DATE) <= DATE_SUB(CAST((SELECT date FROM latest) AS DATE), INTERVAL 90 DAY)
            ORDER BY date DESC
            LIMIT 1
        )
        SELECT 'today' AS period, CAST(latest.date AS STRING) AS date, latest.ihsg_close, 0.0 AS change_pct
        FROM latest
        UNION ALL
        SELECT '30d', CAST(d30.date AS STRING), d30.ihsg_close,
            ROUND((l.ihsg_close - d30.ihsg_close) / d30.ihsg_close * 100, 2)
        FROM d30 CROSS JOIN latest l
        UNION ALL
        SELECT '60d', CAST(d60.date AS STRING), d60.ihsg_close,
            ROUND((l.ihsg_close - d60.ihsg_close) / d60.ihsg_close * 100, 2)
        FROM d60 CROSS JOIN latest l
        UNION ALL
        SELECT '90d', CAST(d90.date AS STRING), d90.ihsg_close,
            ROUND((l.ihsg_close - d90.ihsg_close) / d90.ihsg_close * 100, 2)
        FROM d90 CROSS JOIN latest l
    """
    rows = list(client.query(query).result())
    if not rows:
        raise HTTPException(status_code=404, detail="No IHSG data available")

    order = {"today": 0, "30d": 1, "60d": 2, "90d": 3}
    result = sorted(
        [
            {
                "period": row["period"],
                "date": row["date"],
                "ihsg_close": row["ihsg_close"],
                "change_pct": row["change_pct"],
            }
            for row in rows
        ],
        key=lambda x: order.get(x["period"], 99),
    )
    return result
