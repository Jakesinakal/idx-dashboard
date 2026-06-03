"""
routers/news.py
---------------
Latest Indonesian market-news headlines from the `news_articles` table.
Sentiment fields are added by the Fase 2 AI step; this endpoint returns
them when present and omits them otherwise, so it works before and after.
"""

from fastapi import APIRouter, HTTPException, Query
from google.cloud import bigquery

from database import TABLE_PREFIX, get_client

router = APIRouter()


@router.get("/news")
def get_news(
    limit: int = Query(20, ge=1, le=100, description="Number of articles"),
    source: str | None = Query(None, description="Filter by source name, e.g. 'Kontan'"),
):
    client = get_client()

    filters: list[str] = []
    params: list[bigquery.ScalarQueryParameter] = [
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]
    if source:
        filters.append("source = @source")
        params.append(bigquery.ScalarQueryParameter("source", "STRING", source.strip()))
    where_sql = ("WHERE " + " AND ".join(filters)) if filters else ""

    query = f"""
        SELECT date, title, description, source, url, published_at,
               sentiment_label, sentiment_score
        FROM {TABLE_PREFIX}.news_articles
        {where_sql}
        ORDER BY published_at DESC
        LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = list(client.query(query, job_config=job_config).result())
    if not rows:
        raise HTTPException(status_code=404, detail="No news available")
    return [dict(row) for row in rows]
