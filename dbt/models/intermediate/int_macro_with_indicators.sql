{{ config(materialized='ephemeral') }}

SELECT
    date,
    ihsg_close,
    ihsg_volume,
    cpi_us,
    fed_rate,
    usd_idr,
    eur_idr,
    jpy_idr,
    ihsg_return_pct,
    year,
    month,
    week,

    -- 30-day rolling IHSG return volatility (annualised std dev of daily returns)
    ROUND(
        STDDEV(ihsg_return_pct) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW),
        6
    ) AS ihsg_volatility_30d,

    -- IDR strength: inverse of USD/IDR scaled to [0, 10] range.
    -- Higher value = IDR is stronger relative to USD.
    ROUND(SAFE_DIVIDE(1.0, usd_idr) * 100000, 6) AS idr_strength_index

FROM {{ ref('stg_macro_economic') }}
