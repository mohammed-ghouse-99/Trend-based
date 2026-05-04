"""
project/data/collector.py

Robust data collection from yfinance (OHLCV).

Key behavior:
- Default period = 1y (dashboard, indicators, charts)
- ML requires minimum 3y → enforced via for_ml=True
- User can explicitly request longer periods
"""

from typing import Optional
import yfinance as yf
import pandas as pd
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -----------------------------------------------------
# PERIOD MAP
# -----------------------------------------------------
_PERIOD_MAP = {
    "1y": 1,
    "2y": 2,
    "3y": 3,
    "5y": 5,
    "10y": 10,
    "max": 100
}

_VALID_INTERVALS = {
    "1m", "2m", "5m", "15m", "30m", "60m",
    "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"
}

# -----------------------------------------------------
# PERIOD NORMALIZATION
# -----------------------------------------------------
def _normalize_period(user_period: str, for_ml: bool) -> str:
    # Default fallback
    default_period = "3y" if for_ml else "1y"

    if not isinstance(user_period, str):
        return default_period

    period = user_period.strip().lower()

    if period not in _PERIOD_MAP:
        return default_period

    years = _PERIOD_MAP[period]

    # Enforce ML minimum
    if for_ml and years < 3:
        logger.info("ML requires minimum 3y data. Upgrading period to 3y.")
        return "3y"

    return period

# -----------------------------------------------------
# INTERVAL NORMALIZATION
# -----------------------------------------------------
def _normalize_interval(interval: str) -> str:
    if interval is None:
        return "1d"

    iv = interval.strip().lower()

    if iv == "1h":
        iv = "60m"

    if iv not in _VALID_INTERVALS:
        logger.warning("Unknown interval '%s'. Defaulting to '1d'.", interval)
        return "1d"

    return iv

# -----------------------------------------------------
# MAIN FETCH FUNCTION
# -----------------------------------------------------
def get_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    auto_adjust: bool = False,
    retry: int = 2,
    pause: float = 0.5,
    for_ml: bool = False
) -> Optional[pd.DataFrame]:

    ticker = str(ticker).strip()
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    period = _normalize_period(period, for_ml)
    interval = _normalize_interval(interval)

    last_exception = None

    for attempt in range(retry + 1):
        try:
            logger.info("Downloading %s for %s @ %s", period, ticker, interval)

            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
                progress=False
            )

            if df is None or df.empty:
                logger.warning("No data returned for %s", ticker)
                return None

            # Standardize index
            df.index = pd.to_datetime(df.index, errors="coerce")
            df = df.sort_index()

            # Fix multi-index columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

            # Normalize OHLCV
            required = ["Open", "High", "Low", "Close", "Volume"]
            lower_map = {c.lower(): c for c in df.columns}

            rename_map = {}
            for col in required:
                if col not in df.columns and col.lower() in lower_map:
                    rename_map[lower_map[col.lower()]] = col

            if rename_map:
                df = df.rename(columns=rename_map)

            if "Adj Close" not in df.columns:
                df["Adj Close"] = df["Close"]

            missing = [c for c in required if c not in df.columns]
            if missing:
                logger.error("Missing OHLCV columns: %s", missing)
                return None

            df = df[required + ["Adj Close"]]
            df = df.dropna(subset=required)

            # Remove timezone if any
            if hasattr(df.index, "tz"):
                try:
                    df.index = df.index.tz_convert(None)
                except Exception:
                    pass

            logger.info("Fetched %d rows for %s", len(df), ticker)
            return df

        except Exception as e:
            logger.exception("Fetch error attempt %d: %s", attempt + 1, e)
            last_exception = e
            time.sleep(pause)

    raise RuntimeError(f"Failed to download data for {ticker}") from last_exception
