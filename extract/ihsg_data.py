"""
extract/ihsg_data.py
--------------------
Extracts the IHSG index (^JKSE) and the tracked IDX stock universe (LQ45)
from Yahoo Finance using the yfinance library. Each ticker is downloaded
individually so that errors on one ticker do not block the others.

The ticker list is sourced from ``config.universe`` (single source of truth,
tagged by index) — edit that file to change the universe, not this one.

Returns a unified long-format DataFrame with columns:
    date, ticker, name, close, volume
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

from config.universe import extract_ticker_names

load_dotenv()

# Map ticker symbol -> human-readable name (benchmark + full tracked universe)
TICKERS = extract_ticker_names()


def extract_ihsg(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Downloads IHSG index and IDX stock data from Yahoo Finance.

    Args:
        start_date: Start date in YYYY-MM-DD format. Defaults to 1 year ago.
        end_date:   End date in YYYY-MM-DD format. Defaults to today.

    Returns:
        DataFrame with columns: date, ticker, name, close, volume
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    print(f"[IHSG] Extracting data from {start_date} to {end_date}")

    all_records = []

    for ticker, name in TICKERS.items():
        try:
            print(f"[IHSG] Downloading {ticker} ({name}) ...")
            t = yf.Ticker(ticker)
            hist = t.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"[IHSG] WARNING: No data returned for {ticker}, skipping.")
                continue

            hist = hist.reset_index()

            # 'Date' column may be timezone-aware — normalise to date string
            hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)

            df = pd.DataFrame({
                "date": hist["Date"].dt.strftime("%Y-%m-%d"),
                "ticker": ticker,
                "name": name,
                "close": pd.to_numeric(hist["Close"], errors="coerce"),
                "volume": pd.to_numeric(hist["Volume"], errors="coerce"),
            })

            all_records.append(df)
            print(f"[IHSG] {ticker}: {len(df)} rows fetched.")

        except Exception as e:
            print(f"[IHSG] ERROR fetching {ticker}: {e}")

    if not all_records:
        print("[IHSG] No data was fetched for any ticker.")
        return pd.DataFrame(columns=["date", "ticker", "name", "close", "volume"])

    result = pd.concat(all_records, ignore_index=True).sort_values(
        ["ticker", "date"]
    ).reset_index(drop=True)

    print(f"[IHSG] Total rows extracted: {len(result)}")
    return result
