from fastapi import APIRouter, Query

from database import TABLE_PREFIX, get_client

router = APIRouter()


@router.get("/currency/trend")
def get_currency_trend(days: int = Query(default=30, ge=7, le=365)):
    days = int(days)
    client = get_client()
    query = f"""
        WITH latest AS (
            SELECT MAX(CAST(date AS DATE)) AS max_date
            FROM {TABLE_PREFIX}.currency_rates
        )
        SELECT
            date,
            usd_idr,
            eur_idr,
            jpy_idr
        FROM {TABLE_PREFIX}.currency_rates
        WHERE CAST(date AS DATE) >= DATE_SUB((SELECT max_date FROM latest), INTERVAL {days} DAY)
        ORDER BY date ASC
    """
    rows = list(client.query(query).result())
    return [
        {
            "date": row["date"],
            "usd_idr": row["usd_idr"],
            "eur_idr": row["eur_idr"],
            "jpy_idr": row["jpy_idr"],
        }
        for row in rows
    ]
