import os
import json
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from project.data.providers.base import FinancialData
from project.data.providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 900


class FinancialService:
    def __init__(self, use_cache: bool = True, cache_dir: Optional[str] = None):
        self._use_cache = use_cache
        self._factory = ProviderFactory()
        self._memory_cache: Dict[str, tuple] = {}
        self._cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "project_cache", "financial"
        )
        if use_cache:
            os.makedirs(self._cache_dir, exist_ok=True)

    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        symbol = symbol.upper()
        if self._use_cache:
            cached = self._load_from_cache(symbol)
            if cached:
                return cached
        data = self._factory.fetch_with_fallback(symbol)
        if data and self._use_cache:
            self._save_to_cache(data)
        return data

    def _get_cache_path(self, symbol: str) -> str:
        return os.path.join(self._cache_dir, f"{symbol}.json")

    def _load_from_cache(self, symbol: str) -> Optional[FinancialData]:
        now = time.time()

        mem = self._memory_cache.get(symbol)
        if mem:
            ts, data = mem
            if now - ts < CACHE_TTL_SECONDS:
                return data

        path = self._get_cache_path(symbol)
        if os.path.exists(path):
            try:
                mtime = os.path.getmtime(path)
                if now - mtime < CACHE_TTL_SECONDS:
                    with open(path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    raw.pop("_metadata", None)
                    data = FinancialData(**raw)
                    self._memory_cache[symbol] = (now, data)
                    return data
            except Exception as e:
                logger.warning("Cache read failed for %s: %s", symbol, str(e))

        return None

    def _save_to_cache(self, data: FinancialData) -> None:
        now = time.time()
        self._memory_cache[data.symbol] = (now, data)

        path = self._get_cache_path(data.symbol)
        try:
            raw = data.to_dict()
            raw["_metadata"] = {"cached_at": datetime.now().isoformat()}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2)
        except Exception as e:
            logger.warning("Cache write failed for %s: %s", data.symbol, str(e))

    def clear_cache(self, symbol: Optional[str] = None):
        if symbol:
            self._memory_cache.pop(symbol.upper(), None)
            path = self._get_cache_path(symbol.upper())
            if os.path.exists(path):
                os.remove(path)
        else:
            self._memory_cache.clear()
            if os.path.exists(self._cache_dir):
                for f in os.listdir(self._cache_dir):
                    if f.endswith(".json"):
                        os.remove(os.path.join(self._cache_dir, f))
