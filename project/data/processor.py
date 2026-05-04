"""
project/data/processor.py

This module creates ALL technical indicators used by:
- Machine Learning model (RandomForest / Boosting)
- TrendDetector (rule-based engine)
- Dashboard visualizations

All indicator names use UPPERCASE to ensure consistency across:
training → prediction → trend detection → charts.

Mathematically stable & industry-standard formulas.
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ==========================================================
# 1) SIMPLE MOVING AVERAGE (SMA)
# ----------------------------------------------------------
# SMA_t = (Price[t] + Price[t-1] + ... + Price[t-n+1]) / n
# ==========================================================
def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()


# ==========================================================
# 2) EXPONENTIAL MOVING AVERAGE (EMA)
# ----------------------------------------------------------
# EMA_t = α*Price[t] + (1-α)*EMA[t-1]
# α = 2 / (window+1)
# ==========================================================
def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

# ==========================================================
# 3) RELATIVE STRENGTH INDEX (RSI)
# ----------------------------------------------------------
# RSI = 100 - (100 / (1 + RS))
# RS = AvgGain / AvgLoss
# Uses Wilder smoothing (rolling mean version)
# ==========================================================
def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()

    # gain = positive differences
    gain = delta.clip(lower=0)

    # loss = absolute value of negative differences
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / (avg_loss + 1e-9)  # numerical stability

    return 100 - (100 / (1 + rs))


# ==========================================================
# 4) AVERAGE TRUE RANGE (ATR)
# ----------------------------------------------------------
# True Range (TR) = max(
#   high-low,
#   abs(high-prev_close),
#   abs(low-prev_close)
# )
# ATR = SMA(TR, n)
# ==========================================================
def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return tr.rolling(window=window, min_periods=1).mean()


# ==========================================================
# 5) MACD (Moving Average Convergence Divergence)
# ----------------------------------------------------------
# MACD = EMA_12 - EMA_26
# Signal = EMA_9(MACD)
# Histogram = MACD - Signal
# ==========================================================
def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()

    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal

    return macd, macd_signal, macd_hist


# ==========================================================
# 6) MAIN INDICATOR ENGINE
# ----------------------------------------------------------
# Creates ALL indicators used across project.
# ==========================================================
def add_indicators(df: pd.DataFrame, dropna: bool = True) -> pd.DataFrame:
    df = df.copy()

    # ensure required columns exist
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        raise ValueError(f"Data missing required OHLCV columns: {required}")

    # =======================
    # MOVING AVERAGES
    # =======================
    df["SMA_10"] = _sma(df["Close"], 10)
    df["SMA_20"] = _sma(df["Close"], 20)
    df["SMA_50"] = _sma(df["Close"], 50)
    df["SMA_200"] = _sma(df["Close"], 200)

    df["SMA_14"] = _sma(df["Close"], 14)  # used in ML basic version

    # =======================
    # EXPONENTIAL MOVING AVERAGES
    # =======================
    df["EMA_10"] = _ema(df["Close"], 10)
    df["EMA_20"] = _ema(df["Close"], 20)
    df["EMA_50"] = _ema(df["Close"], 50)

    # =======================
    # RSI (14)
    # =======================
    df["RSI_14"] = _rsi(df["Close"], 14)

    # =======================
    # ATR (14)
    # =======================
    df["ATR_14"] = _atr(df, 14)

    # =======================
    # MACD
    # =======================
    macd, macd_signal, macd_hist = _macd(df["Close"])
    df["MACD"] = macd
    df["MACD_SIGNAL"] = macd_signal
    df["MACD_HIST"] = macd_hist

    # =======================
    # RETURNS & VOLATILITY
    # =======================
    df["RETURNS"] = df["Close"].pct_change()
    df["VOL_20"] = df["RETURNS"].rolling(20).std()

    # =======================
    # MOMENTUM
    # =======================
    df["MOMENTUM_5"] = df["Close"].diff(5)
    df["MOMENTUM_10"] = df["Close"].diff(10)

    # =======================
    # SLOPE (Linear Regression Slope)
    # =======================
    def slope(series):
        y = series.values
        x = np.arange(len(y))
        if len(y) < 2:
            return np.nan
        return np.polyfit(x, y, 1)[0]  # slope only

    df["SLOPE_20"] = df["Close"].rolling(20, min_periods=5).apply(slope, raw=False)

    # =======================
    # NORMALIZED RATIOS
    # =======================
    df["CLOSE_OVER_SMA50"] = df["Close"] / (df["SMA_50"] + 1e-9)
    df["SMA50_OVER_SMA200"] = df["SMA_50"] / (df["SMA_200"] + 1e-9)

    if dropna:
        df = df.dropna()

    logger.info(f"Indicators added: {len(df.columns)} columns")
    return df
