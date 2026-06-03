"""
extract/currency_data.py
------------------------
Fetches three currency pairs from Yahoo Finance using yfinance:
    IDR=X    — USD / IDR  (how many IDR per 1 USD)
    EURIDR=X — EUR / IDR
    JPYIDR=X — JPY / IDR

Each ticker is downloaded individually so that a failure on one pair
does not prevent the others from being collected.

Returns a DataFrame with columns: date, usd_idr, eur_idr, jpy_idr
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

# Maps Yahoo Finance ticker -> output column name
CURRENCY_TICKERS = {
    "IDR=X":    "usd_idr",
    "EURIDR=X": "eur_idr",
    "JPYIDR=X": "jpy_idr",
}


def extract_currency(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Downloads IDR/USD, EUR/IDR, and JPY/IDR exchange rates from Yahoo Finance.

    Args:
        start_date: Start date in YYYY-MM-DD format. Defaults to 1 year ago.
        end_date:   End date in YYYY-MM-DD format. Defaults to today.

    Returns:
        DataFrame with columns: date, usd_idr, eur_idr, jpy_idr
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    print(f"[Currency] Extracting data from {start_date} to {end_date}")

    col_names = list(CURRENCY_TICKERS.values())
    merged: pd.DataFrame | None = None

    for ticker, col_name in CURRENCY_TICKERS.items():
        try:
            print(f"[Currency] Downloading {ticker} -> {col_name} ...")
            t = yf.Ticker(ticker)
            hist = t.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"[Currency] WARNING: No data for {ticker}, skipping.")
                continue

            hist = hist.reset_index()

            # Normalise timezone-aware DatetimeIndex
            hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)

            df = pd.DataFrame({
                "date":   hist["Date"].dt.strftime("%Y-%m-%d"),
                col_name: pd.to_numeric(hist["Close"], errors="coerce"),
            })

            print(f"[Currency] {ticker}: {len(df)} rows fetched.")

            merged = df if merged is None else pd.merge(merged, df, on="date", how="outer")

        except Exception as e:
            print(f"[Currency] ERROR fetching {ticker}: {e}")

    if merged is None or merged.empty:
        print("[Currency] No data was fetched.")
        return pd.DataFrame(columns=["date"] + col_names)

    # Ensure all expected columns exist even if some tickers failed
    for col in col_names:
        if col not in merged.columns:
            merged[col] = float("nan")

    result = merged[["date"] + col_names].sort_values("date").reset_index(drop=True)
    print(f"[Currency] Total rows extracted: {len(result)}")
    return result
