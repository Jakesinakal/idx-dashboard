"""
extract/fred_data.py
--------------------
Fetches three macroeconomic series from the FRED REST API:
    CPIAUCSL  — US CPI Inflation (monthly)
    FEDFUNDS  — Federal Funds Rate (monthly)
    DEXINUS   — USD / IDR exchange rate (daily)

The FRED API returns "." for missing observations; these are converted to NaN.
All three series are outer-merged on the date column so no observations are lost.

Returns a DataFrame with columns: date, cpi_us, fed_rate, usd_idr_fred
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# Maps FRED series ID -> output column name
SERIES = {
    "CPIAUCSL": "cpi_us",
    "FEDFUNDS": "fed_rate",
    "DEXINUS":  "usd_idr_fred",
}


def _fetch_series(series_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches a single FRED series and returns a two-column DataFrame:
    ['date', <series_id>].
    """
    params = {
        "series_id":          series_id,
        "api_key":            FRED_API_KEY,
        "file_type":          "json",
        "observation_start":  start_date,
        "observation_end":    end_date,
    }

    print(f"[FRED] Requesting series: {series_id}")
    response = requests.get(FRED_BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    observations = response.json().get("observations", [])

    if not observations:
        print(f"[FRED] WARNING: No observations returned for {series_id}.")
        return pd.DataFrame(columns=["date", series_id])

    df = pd.DataFrame(observations)[["date", "value"]].copy()

    # FRED uses "." to represent missing values
    df["value"] = df["value"].replace(".", None)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.rename(columns={"value": series_id})

    print(f"[FRED] {series_id}: {len(df)} observations fetched.")
    return df


def extract_fred(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Downloads CPIAUCSL, FEDFUNDS, and DEXINUS from the FRED API.

    Args:
        start_date: Start date in YYYY-MM-DD format. Defaults to 1 year ago.
        end_date:   End date in YYYY-MM-DD format. Defaults to today.

    Returns:
        DataFrame with columns: date, cpi_us, fed_rate, usd_idr_fred
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    print(f"[FRED] Extracting data from {start_date} to {end_date}")

    try:
        series_dfs = [
            _fetch_series(series_id, start_date, end_date)
            for series_id in SERIES
        ]

        # Outer-merge so all dates from all series are retained
        result = series_dfs[0]
        for df in series_dfs[1:]:
            result = pd.merge(result, df, on="date", how="outer")

        # Rename series IDs to friendly column names
        result = result.rename(columns=SERIES)
        result = result.sort_values("date").reset_index(drop=True)

        print(f"[FRED] Total rows extracted: {len(result)}")
        return result

    except Exception as e:
        print(f"[FRED] ERROR: {e}")
        return pd.DataFrame(columns=["date", "cpi_us", "fed_rate", "usd_idr_fred"])
