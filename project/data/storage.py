"""
project/data/storage.py

Simple but robust caching layer to avoid repeated yfinance downloads during development and for Streamlit UX.
Supports:
- Pickle caching with timestamp check (max_age_days)
- CSV fallback
- Atomic write handling
"""

import os
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import os as _os
_VERCEL = _os.environ.get("VERCEL") == "1"
CACHE_DIR = Path(_os.environ.get("CACHE_DIR", "/tmp/project_cache" if _VERCEL else str(Path.cwd() / "project_cache")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(ticker: str, period: str, interval: str, filetype: str = "pkl") -> Path:
    safe_ticker = ticker.replace("/", "_").replace(":", "_")
    name = f"{safe_ticker}__{period}__{interval}.{filetype}"
    return CACHE_DIR / name


def save_cache(df: pd.DataFrame, ticker: str, period: str, interval: str) -> Path:
    """
    Save DataFrame to cache as pickle. Overwrites existing file atomically.
    Returns path to saved file.
    """
    path = _cache_path(ticker, period, interval, "pkl")
    tmp = path.with_suffix(".pkl.tmp")
    try:
        with tmp.open("wb") as f:
            pickle.dump(df, f)
        tmp.replace(path)
        logger.info("Cache saved: %s", path)
        return path
    except Exception as e:
        logger.exception("Failed to write cache: %s", e)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def load_cache(ticker: str, period: str, interval: str, max_age_days: int = 1) -> pd.DataFrame | None:
    """
    Load cached DataFrame if found and fresh (modification time < max_age_days).
    Returns None if not found or stale.
    """
    path = _cache_path(ticker, period, interval, "pkl")
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    if datetime.now() - mtime > timedelta(days=max_age_days):
        logger.info("Cache expired for %s (mtime=%s)", path, mtime)
        return None
    try:
        with path.open("rb") as f:
            df = pickle.load(f)
        logger.info("Loaded cache: %s rows=%d", path, len(df))
        return df
    except Exception as e:
        logger.exception("Failed to load cache file %s: %s", path, e)
        return None


def clear_cache():
    for f in CACHE_DIR.iterdir():
        try:
            f.unlink()
        except Exception:
            pass
    logger.info("All cache cleared")
