"""
routers/screener.py
--------------------
The stock screener: serves the per-ticker technical-signal snapshot from the
`stock_signals` table, with universe / signal filters and sortable columns.
"""

from fastapi import APIRouter, HTTPException, Query
from google.cloud import bigquery

from database import TABLE_PREFIX, get_client

router = APIRouter()

# Whitelist of sortable columns (can't parameterize an ORDER BY column, so we
# map a safe key -> real column to avoid SQL injection).
_SORT_COLUMNS = {
    "return":   "return_1d",
    "rsi":      "rsi14",
    "momentum": "momentum_20d",
    "close":    "close",
    "ticker":   "ticker",
    "signal":   "signal",
}
_VALID_SIGNALS = {"BUY", "HOLD", "SELL", "OVERBOUGHT"}


@router.get("/screener")
def get_screener(
    universe: str = Query("LQ45", description="Index universe: LQ45, JII70, or ALL"),
    signal: str | None = Query(None, description="Filter by signal: BUY / HOLD / SELL / OVERBOUGHT"),
    sort: str = Query("return", description="Sort key: return, rsi, momentum, close, ticker, signal"),
    order: str = Query("desc", description="Sort direction: asc or desc"),
):
    client = get_client()

    filters: list[str] = []
    params: list[bigquery.ScalarQueryParameter] = []

    u = universe.strip().upper()
    if u and u != "ALL":
        filters.append("index_membership LIKE @universe")
        params.append(bigquery.ScalarQueryParameter("universe", "STRING", f"%{u}%"))

    if signal:
        s = signal.strip().upper()
        if s not in _VALID_SIGNALS:
            raise HTTPException(status_code=400, detail=f"Invalid signal '{signal}'. Use one of {sorted(_VALID_SIGNALS)}")
        filters.append("UPPER(signal) = @signal")
        params.append(bigquery.ScalarQueryParameter("signal", "STRING", s))

    where_sql = ("WHERE " + " AND ".join(filters)) if filters else ""
    sort_col = _SORT_COLUMNS.get(sort.lower(), "return_1d")
    order_sql = "ASC" if order.lower() == "asc" else "DESC"

    query = f"""
        SELECT
            CAST(date AS STRING) AS date,
            ticker, name, index_membership,
            close,
            ROUND(return_1d, 2)    AS return_pct,
            volume,
            ROUND(vol_avg20, 0)    AS vol_avg20,
            ROUND(ma20, 2)         AS ma20,
            ROUND(ma50, 2)         AS ma50,
            ROUND(ma200, 2)        AS ma200,
            ma_trend,
            ROUND(rsi14, 1)        AS rsi,
            ROUND(momentum_20d, 2) AS momentum_pct,
            ROUND(high_52w, 2)     AS high_52w,
            ROUND(low_52w, 2)      AS low_52w,
            signal
        FROM {TABLE_PREFIX}.stock_signals
        {where_sql}
        ORDER BY {sort_col} {order_sql}
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = list(client.query(query, job_config=job_config).result())
    if not rows:
        raise HTTPException(status_code=404, detail="No signal data available")

    return [dict(row) for row in rows]
