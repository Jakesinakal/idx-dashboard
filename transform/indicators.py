"""
transform/indicators.py
------------------------
Pure technical-indicator functions for the IDX stock universe.

Operates on a long-format DataFrame (one row per date+ticker) with at least
the columns ``date, ticker, close, volume``. Every function here is
side-effect free, so the maths can be unit-tested without touching BigQuery;
the ``bq_stock_signals`` Dagster asset wires these into the warehouse.

Indicators produced: MA20/50/200, Wilder RSI(14), 20-day average volume,
20-day momentum, 52-week high/low, and the 1-day return. A transparent rule
set (see ``classify_signal``) then maps those to a BUY / HOLD / SELL /
OVERBOUGHT signal so the screener's decisions are explainable, not a black box.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# --- Tunables: kept in one place so the rules stay transparent -------------
MA_WINDOWS = (20, 50, 200)        # moving-average lookbacks (trading days)
RSI_PERIOD = 14
VOL_AVG_WINDOW = 20
MOMENTUM_WINDOW = 20              # % change over ~1 trading month
WEEK52_WINDOW = 252              # ~ trading days in a year
RSI_OVERBOUGHT = 70.0
RSI_OVERSOLD = 30.0

# Signal labels
BUY, HOLD, SELL, OVERBOUGHT = "BUY", "HOLD", "SELL", "OVERBOUGHT"

# Required input columns
REQUIRED_COLUMNS = ("date", "ticker", "close", "volume")


def _wilder_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Wilder's RSI — EWM with alpha = 1/period (adjust=False) is Wilder smoothing."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # all-gains window -> avg_loss == 0 -> RSI saturates at 100
    return rsi.where(avg_loss != 0, 100.0)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with per-ticker indicator columns added.

    Indicators are computed within each ticker, in date order, so one ticker's
    history never leaks into another's.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"add_indicators: missing required columns {missing}")

    out = df.copy()
    out["date"] = out["date"].astype(str)
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce")
    out = out.sort_values(["ticker", "date"]).reset_index(drop=True)

    g = out.groupby("ticker", group_keys=False)
    for w in MA_WINDOWS:
        out[f"ma{w}"] = g["close"].transform(lambda s, w=w: s.rolling(w, min_periods=w).mean())
    out["rsi14"] = g["close"].transform(_wilder_rsi)
    out["vol_avg20"] = g["volume"].transform(
        lambda s: s.rolling(VOL_AVG_WINDOW, min_periods=VOL_AVG_WINDOW).mean()
    )
    out["return_1d"] = g["close"].transform(lambda s: s.pct_change() * 100.0)
    out["momentum_20d"] = g["close"].transform(lambda s: s.pct_change(MOMENTUM_WINDOW) * 100.0)
    out["high_52w"] = g["close"].transform(lambda s: s.rolling(WEEK52_WINDOW, min_periods=1).max())
    out["low_52w"] = g["close"].transform(lambda s: s.rolling(WEEK52_WINDOW, min_periods=1).min())
    return out


def classify_signal(row: pd.Series) -> str:
    """Map one indicator row to a signal. Order matters (first match wins):

      OVERBOUGHT : RSI >= 70                       (extended — caution)
      SELL       : close < MA50                    (below medium-term trend)
      BUY        : close > MA20 > MA50 & RSI < 70  (aligned uptrend, not extended)
      HOLD       : anything else / not enough data
    """
    close, ma20, ma50, rsi = row.get("close"), row.get("ma20"), row.get("ma50"), row.get("rsi14")
    if pd.isna(close) or pd.isna(ma50):       # not enough history to judge a trend
        return HOLD
    if not pd.isna(rsi) and rsi >= RSI_OVERBOUGHT:
        return OVERBOUGHT
    if close < ma50:
        return SELL
    if not pd.isna(ma20) and close > ma20 and ma20 > ma50:
        return BUY
    return HOLD


def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``ma_trend`` (Bull/Bear/Unknown) and ``signal`` columns."""
    out = df.copy()
    out["ma_trend"] = np.where(out["close"] >= out["ma50"], "Bull", "Bear")
    out.loc[out["ma50"].isna(), "ma_trend"] = "Unknown"
    out["signal"] = out.apply(classify_signal, axis=1)
    return out


def latest_per_ticker(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent row per ticker (by date)."""
    return (
        df.sort_values(["ticker", "date"])
        .groupby("ticker", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )


def compute_signal_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Full pipeline: indicators -> signals -> latest row per ticker (one row/ticker)."""
    return latest_per_ticker(add_signals(add_indicators(df)))
