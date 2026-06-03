"""
routers/briefing.py
--------------------
The daily AI market briefing — the dashboard's hero card. Serves the most
recent narrative from the `daily_briefing` table.
"""

from fastapi import APIRouter, HTTPException

from database import TABLE_PREFIX, get_client

router = APIRouter()


@router.get("/briefing")
def get_briefing():
    client = get_client()
    query = f"""
        SELECT CAST(date AS STRING) AS date, narrative, ihsg_return_pct,
               news_mood, generated_at
        FROM {TABLE_PREFIX}.daily_briefing
        ORDER BY date DESC
        LIMIT 1
    """
    rows = list(client.query(query).result())
    if not rows:
        raise HTTPException(status_code=404, detail="No briefing available")
    return dict(rows[0])
