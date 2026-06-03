{{ config(materialized='view') }}

-- usd_idr_fred is excluded: FRED reports IDR/USD in a different unit than yfinance.
-- cpi_us and fed_rate are forward-filled here because the source table has ~47 leading
-- nulls where the backfill window predates the first FRED monthly observation.

WITH base AS (
    SELECT
        CAST(date         AS DATE)                         AS date,
        ROUND(CAST(ihsg_close     AS FLOAT64), 2)          AS ihsg_close,
        CAST(ihsg_volume  AS INT64)                        AS ihsg_volume,
        CAST(cpi_us       AS FLOAT64)                      AS cpi_us,
        CAST(fed_rate     AS FLOAT64)                      AS fed_rate,
        ROUND(CAST(usd_idr        AS FLOAT64), 2)          AS usd_idr,
        ROUND(CAST(eur_idr        AS FLOAT64), 2)          AS eur_idr,
        ROUND(CAST(jpy_idr        AS FLOAT64), 6)          AS jpy_idr,
        ROUND(CAST(ihsg_return_pct AS FLOAT64), 4)         AS ihsg_return_pct,
        CAST(year         AS INT64)                        AS year,
        CAST(month        AS INT64)                        AS month,
        CAST(week         AS INT64)                        AS week
    FROM {{ source('financial_data', 'macro_economic_daily') }}
)

SELECT
    date,
    ihsg_close,
    ihsg_volume,
    ROUND(
        LAST_VALUE(cpi_us IGNORE NULLS) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
        4
    ) AS cpi_us,
    ROUND(
        LAST_VALUE(fed_rate IGNORE NULLS) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
        4
    ) AS fed_rate,
    usd_idr,
    eur_idr,
    jpy_idr,
    ihsg_return_pct,
    year,
    month,
    week
FROM base
