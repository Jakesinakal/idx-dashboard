from fastapi import APIRouter, HTTPException

from database import TABLE_PREFIX, get_client

router = APIRouter()


@router.get("/stocks/today")
def get_stocks_today():
    client = get_client()
    query = f"""
        WITH latest_date AS (
            SELECT MAX(date) AS max_date
            FROM {TABLE_PREFIX}.stock_performance
        ),
        prev_trading_day AS (
            SELECT MAX(date) AS d
            FROM {TABLE_PREFIX}.stock_performance
            WHERE date < (SELECT max_date FROM latest_date)
        ),
        today AS (
            SELECT ticker, name, close, volume, date
            FROM {TABLE_PREFIX}.stock_performance
            WHERE date = (SELECT max_date FROM latest_date)
        ),
        prev AS (
            SELECT ticker, close AS prev_close
            FROM {TABLE_PREFIX}.stock_performance
            WHERE date = (SELECT d FROM prev_trading_day)
        ),
        ihsg AS (
            SELECT ihsg_return_pct
            FROM {TABLE_PREFIX}.macro_economic_daily
            WHERE date = (SELECT max_date FROM latest_date)
        )
        SELECT
            t.ticker,
            t.name,
            t.close,
            t.volume,
            CAST(t.date AS STRING) AS date,
            ROUND((t.close - p.prev_close) / p.prev_close * 100, 2) AS return_pct,
            i.ihsg_return_pct,
            CASE
                WHEN ROUND((t.close - p.prev_close) / p.prev_close * 100, 2) > IFNULL(i.ihsg_return_pct, 0) + 0.5
                    THEN 'outperform'
                WHEN ROUND((t.close - p.prev_close) / p.prev_close * 100, 2) < IFNULL(i.ihsg_return_pct, 0) - 0.5
                    THEN 'underperform'
                ELSE 'neutral'
            END AS vs_ihsg
        FROM today t
        LEFT JOIN prev p ON t.ticker = p.ticker
        LEFT JOIN ihsg i ON TRUE
        ORDER BY return_pct DESC
    """
    rows = list(client.query(query).result())
    if not rows:
        raise HTTPException(status_code=404, detail="No stock data available")
    return [
        {
            "ticker": row["ticker"],
            "name": row["name"],
            "close": row["close"],
            "volume": row["volume"],
            "date": row["date"],
            "return_pct": row["return_pct"],
            "ihsg_return_pct": row["ihsg_return_pct"],
            "vs_ihsg": row["vs_ihsg"],
        }
        for row in rows
    ]
