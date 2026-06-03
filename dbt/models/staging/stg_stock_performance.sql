{{ config(materialized='view') }}

SELECT
    CAST(date   AS DATE)                     AS date,
    CAST(ticker AS STRING)                   AS ticker,
    CAST(name   AS STRING)                   AS name,
    ROUND(CAST(close  AS FLOAT64), 2)        AS close,
    CAST(volume AS INT64)                    AS volume,
    CAST(year   AS INT64)                    AS year,
    CAST(month  AS INT64)                    AS month
FROM {{ source('financial_data', 'stock_performance') }}
