from fastapi import APIRouter, HTTPException

from database import TABLE_PREFIX, get_client

router = APIRouter()


@router.get("/snapshot")
def get_snapshot():
    client = get_client()
    query = f"""
        SELECT date, ihsg_close, ihsg_return_pct, usd_idr, fed_rate, cpi_us
        FROM {TABLE_PREFIX}.macro_economic_daily
        ORDER BY date DESC
        LIMIT 1
    """
    rows = list(client.query(query).result())
    if not rows:
        raise HTTPException(status_code=404, detail="No data available")
    row = rows[0]

    # Market breadth: how many tracked stocks rose vs fell on the latest day.
    breadth_rows = list(client.query(f"""
        SELECT
            COUNTIF(return_1d > 0) AS advancers,
            COUNTIF(return_1d < 0) AS decliners,
            COUNTIF(return_1d = 0) AS unchanged,
            COUNT(*)               AS total
        FROM {TABLE_PREFIX}.stock_signals
    """).result())
    breadth = dict(breadth_rows[0]) if breadth_rows else None

    # News sentiment: the market mood from the AI-scored headlines.
    sentiment_rows = list(client.query(f"""
        SELECT
            ROUND(AVG(sentiment_score), 3)            AS mood,
            COUNT(*)                                  AS scored,
            COUNTIF(sentiment_label = 'positif')      AS positif,
            COUNTIF(sentiment_label = 'negatif')      AS negatif,
            COUNTIF(sentiment_label = 'netral')       AS netral
        FROM {TABLE_PREFIX}.news_articles
        WHERE sentiment_label IS NOT NULL
    """).result())
    sentiment = dict(sentiment_rows[0]) if sentiment_rows and sentiment_rows[0]["scored"] else None

    return {
        "date": str(row["date"]),
        "ihsg_close": row["ihsg_close"],
        "ihsg_return_pct": row["ihsg_return_pct"],
        "usd_idr": row["usd_idr"],
        "fed_rate": row["fed_rate"],
        "cpi_us": row["cpi_us"],
        "breadth": breadth,
        "sentiment": sentiment,
    }
