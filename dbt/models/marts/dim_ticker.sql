{{ config(materialized='table') }}

SELECT ticker, name, sector, exchange
FROM UNNEST([
    STRUCT('BBCA.JK' AS ticker, 'Bank BCA'           AS name, 'Banking'    AS sector, 'IDX' AS exchange),
    STRUCT('BBRI.JK' AS ticker, 'Bank BRI'           AS name, 'Banking'    AS sector, 'IDX' AS exchange),
    STRUCT('TLKM.JK' AS ticker, 'Telkom Indonesia'   AS name, 'Telecom'    AS sector, 'IDX' AS exchange),
    STRUCT('ASII.JK' AS ticker, 'Astra International' AS name, 'Automotive' AS sector, 'IDX' AS exchange)
])
