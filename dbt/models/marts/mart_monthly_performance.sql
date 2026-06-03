{{
    config(
        materialized='table',
        partition_by={'field': 'month_start', 'data_type': 'date'}
    )
}}

SELECT
    year,
    month,
    -- Synthetic DATE for partition and Looker Studio time dimension
    DATE(year, month, 1)              AS month_start,
    ticker,
    name,
    COUNT(*)                          AS trading_days,
    ROUND(AVG(close), 2)              AS avg_close,
    ROUND(MIN(close), 2)              AS min_close,
    ROUND(MAX(close), 2)              AS max_close,
    ROUND(SUM(CAST(volume AS FLOAT64)), 0) AS total_volume,
    ROUND(AVG(daily_return), 4)       AS avg_daily_return,
    ROUND(STDDEV(daily_return), 4)    AS return_volatility,
    ROUND(AVG(ma_30d), 2)             AS avg_ma_30d
FROM {{ ref('fct_daily_market') }}
GROUP BY year, month, ticker, name
