"""
transform/data_transform.py
---------------------------
Joins and enriches data from the three extract layers into a single,
analysis-ready DataFrame that is loaded into BigQuery.

Steps performed:
    1. Isolate the ^JKSE index rows from the IHSG extract (join key).
    2. Left-join IHSG (daily) ← FRED (monthly) ← Currency (daily) on date.
    3. Forward-fill cpi_us and fed_rate to propagate monthly values across
       trading days.
    4. Drop rows where ihsg_close or usd_idr is null (market closed / no FX).
    5. Add derived columns: year, month, week.

ihsg_return_pct is NOT computed here. It is calculated in BigQuery after
every load using LAG() over the full table, so incremental runs never
produce NaN for the first day of each batch window.

Output columns:
    date, ihsg_close, ihsg_volume,
    cpi_us, fed_rate, usd_idr_fred,
    usd_idr, eur_idr, jpy_idr,
    year, month, week
"""

import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def transform_data(
    ihsg_df: pd.DataFrame,
    fred_df: pd.DataFrame,
    currency_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Joins and transforms the three raw DataFrames into a clean, unified table.

    Args:
        ihsg_df:     Output of extract_ihsg (all tickers, long format).
        fred_df:     Output of extract_fred (date, cpi_us, fed_rate, usd_idr_fred).
        currency_df: Output of extract_currency (date, usd_idr, eur_idr, jpy_idr).

    Returns:
        Transformed DataFrame ready for BigQuery load.
    """
    print("[Transform] Starting transformation pipeline ...")

    # ------------------------------------------------------------------
    # 1. Filter IHSG DataFrame to ^JKSE only for use as the join base
    # ------------------------------------------------------------------
    jkse_df = ihsg_df[ihsg_df["ticker"] == "^JKSE"].copy()
    jkse_df = jkse_df.rename(columns={"close": "ihsg_close", "volume": "ihsg_volume"})
    jkse_df = jkse_df[["date", "ihsg_close", "ihsg_volume"]].copy()
    jkse_df["date"] = jkse_df["date"].astype(str)
    print(f"[Transform] ^JKSE rows (join base): {len(jkse_df)}")

    # ------------------------------------------------------------------
    # 2. Normalise date columns
    # ------------------------------------------------------------------
    fred_df = fred_df.copy()
    currency_df = currency_df.copy()
    fred_df["date"] = fred_df["date"].astype(str)
    currency_df["date"] = currency_df["date"].astype(str)

    # ------------------------------------------------------------------
    # 3. Left join: IHSG ← FRED
    # ------------------------------------------------------------------
    merged = pd.merge(jkse_df, fred_df, on="date", how="left")
    print(f"[Transform] After IHSG + FRED join: {len(merged)} rows")

    # ------------------------------------------------------------------
    # 4. Left join: result ← Currency
    # ------------------------------------------------------------------
    merged = pd.merge(merged, currency_df, on="date", how="left")
    print(f"[Transform] After adding Currency data: {len(merged)} rows")

    # ------------------------------------------------------------------
    # 5. Sort before forward-fill (ffill requires chronological order)
    # ------------------------------------------------------------------
    merged = merged.sort_values("date").reset_index(drop=True)

    # ------------------------------------------------------------------
    # 6. Forward-fill monthly FRED series across daily trading dates
    # ------------------------------------------------------------------
    merged["cpi_us"] = merged["cpi_us"].ffill()
    merged["fed_rate"] = merged["fed_rate"].ffill()
    print("[Transform] Forward-fill applied to cpi_us and fed_rate.")

    # ------------------------------------------------------------------
    # 7. Drop rows with null ihsg_close or usd_idr
    # ------------------------------------------------------------------
    before = len(merged)
    merged = merged.dropna(subset=["ihsg_close", "usd_idr"])
    print(f"[Transform] Dropped {before - len(merged)} rows with null ihsg_close or usd_idr.")

    # ------------------------------------------------------------------
    # 8. Add derived columns
    # ------------------------------------------------------------------
    merged["date"] = pd.to_datetime(merged["date"])
    merged["year"] = merged["date"].dt.year
    merged["month"] = merged["date"].dt.month
    merged["week"] = merged["date"].dt.isocalendar().week.astype(int)
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")

    merged = merged.reset_index(drop=True)
    print(f"[Transform] Transformation complete. Final row count: {len(merged)}")
    return merged
