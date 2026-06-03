{{ config(materialized='ephemeral') }}

SELECT
    date,
    ticker,
    name,
    close,
    volume,
    year,
    month,

    -- Daily return vs previous trading session (per ticker)
    ROUND(
        SAFE_DIVIDE(
            close - LAG(close) OVER (PARTITION BY ticker ORDER BY date),
            LAG(close) OVER (PARTITION BY ticker ORDER BY date)
        ) * 100,
        4
    ) AS daily_return,

    -- 7-day and 30-day simple moving averages (per ticker)
    ROUND(AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 6  PRECEDING AND CURRENT ROW), 2) AS ma_7d,
    ROUND(AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS ma_30d

FROM {{ ref('stg_stock_performance') }}
