import os
import json
import time
import dataclasses
import logging
from typing import Optional, Dict, Any
from project.core.halal.models import StockData
from project.data.providers.financial_service import FinancialService

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "project_cache", "halal")
CACHE_TTL = 86400

logger = logging.getLogger(__name__)


class DataProvider:
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self._service = FinancialService(use_cache=use_cache)
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)

    def _get_cache_path(self, symbol: str) -> str:
        return os.path.join(CACHE_DIR, f"{symbol.upper()}.json")

    def _load_from_cache(self, symbol: str) -> Optional[StockData]:
        path = self._get_cache_path(symbol)
        if os.path.exists(path):
            if time.time() - os.path.getmtime(path) < CACHE_TTL:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data.pop("_metadata", {})
                    return StockData(**data)
                except Exception:
                    pass
        return None

    def _save_to_cache(self, stock: StockData, metadata: Optional[Dict] = None) -> None:
        path = self._get_cache_path(stock.symbol)
        try:
            data = dataclasses.asdict(stock)
            if metadata:
                data["_metadata"] = metadata
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def fetch_stock_data(self, symbol: str) -> Optional[StockData]:
        symbol = symbol.upper()

        if self.use_cache:
            cached = self._load_from_cache(symbol)
            if cached:
                return cached

        financial_data = self._service.get_financial_data(symbol)
        if financial_data:
            stock = self._to_stock_data(financial_data)
            if self.use_cache:
                self._save_to_cache(stock)
            return stock

        return None

    def _to_stock_data(self, data) -> StockData:
        mapping = data.to_halal_dict()
        desc = mapping.get("description") or mapping.get("business_description", "")
        return StockData(
            symbol=mapping["symbol"],
            sector=mapping.get("sector", ""),
            industry=mapping.get("industry", ""),
            business_description=desc,
            description=desc,
            marketCap=mapping.get("marketCap") or 0.0,
            totalDebt=mapping.get("totalDebt") or 0.0,
            totalRevenue=mapping.get("totalRevenue") or 0.0,
            interestIncome=mapping.get("interestIncome"),
            interestExpense=mapping.get("interestExpense"),
            cash=mapping.get("cash") or 0.0,
            receivables=mapping.get("receivables") or 0.0,
            totalAssets=mapping.get("totalAssets") or 0.0,
        )


def enrich_stock_data(symbol: str) -> dict:
    from project.core.halal.engine import HalalEngine

    provider = DataProvider()
    stock_data = provider.fetch_stock_data(symbol)

    if not stock_data:
        return {"symbol": symbol, "error": "Insufficient data from providers"}

    engine = HalalEngine()
    stock_dict = dataclasses.asdict(stock_data)
    result_dict = engine.evaluate(stock_dict)

    return result_dict
