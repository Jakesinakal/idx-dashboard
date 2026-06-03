"""
routers/movers.py
-----------------
Top gainers and losers for the Beranda "Top Movers" panel, by 1-day return,
within the selected index universe.
"""

from fastapi import APIRouter, HTTPException, Query
from google.cloud import bigquery

from database import TABLE_PREFIX, get_client

router = APIRouter()


@router.get("/movers")
def get_movers(
    universe: str = Query("LQ45", description="Index universe: LQ45, JII70, or ALL"),
    limit: int = Query(5, ge=1, le=20, description="Number of gainers and of losers to return"),
):
    client = get_client()

    filters: list[str] = []
    params: list[bigquery.ScalarQueryParameter] = []
    u = universe.strip().upper()
    if u and u != "ALL":
        filters.append("index_membership LIKE @universe")
        params.append(bigquery.ScalarQueryParameter("universe", "STRING", f"%{u}%"))
    where_sql = ("WHERE " + " AND ".join(filters)) if filters else ""

    # Pull the (small) universe once, ordered by return, then slice both ends.
    query = f"""
        SELECT ticker, name, close, ROUND(return_1d, 2) AS return_pct, signal
        FROM {TABLE_PREFIX}.stock_signals
        {where_sql}
        ORDER BY return_1d DESC
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = [dict(r) for r in client.query(query, job_config=job_config).result()]
    if not rows:
        raise HTTPException(status_code=404, detail="No signal data available")

    gainers = [r for r in rows if (r["return_pct"] or 0) > 0][:limit]
    losers = [r for r in rows if (r["return_pct"] or 0) < 0][-limit:][::-1]  # most negative first
    return {"gainers": gainers, "losers": losers}
