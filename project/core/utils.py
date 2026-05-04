"""
project/core/utils.py

Small reusable helpers for the core package.
"""

import pandas as pd
import numpy as np
from typing import Iterable

def require_columns(df: pd.DataFrame, cols: Iterable[str]):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

def last_n(df: pd.DataFrame, n: int=1) -> pd.DataFrame:
    return df.tail(n)

def encode_trend_label(trend_str: str) -> int:
    # mapping for ML label convenience
    return {"UPTREND": 1, "SIDEWAYS": 0, "DOWNTREND": -1}.get(trend_str, 0)
