{{
    config(
        materialized='table',
        partition_by={'field': 'date', 'data_type': 'date'},
        cluster_by=['ticker']
    )
}}

SELECT
    s.date,
    s.ticker,
    s.name,
    s.close,
    s.volume,
    s.daily_return,
    s.ma_7d,
    s.ma_30d,
    m.ihsg_close,
    m.ihsg_return_pct,
    m.cpi_us,
    m.fed_rate,
    m.usd_idr,
    m.eur_idr,
    m.jpy_idr,
    m.ihsg_volatility_30d,
    m.idr_strength_index,
    s.year,
    s.month
FROM {{ ref('int_stock_with_returns') }} AS s
LEFT JOIN {{ ref('int_macro_with_indicators') }} AS m
    ON s.date = m.date
