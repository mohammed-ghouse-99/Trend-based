import logging
from typing import Dict, Any, Optional
import dataclasses

from project.core.halal.data_provider import DataProvider
from project.core.halal.engine import HalalEngine

logger = logging.getLogger(__name__)


def screen_stock(symbol: str, use_cache: bool = True) -> Dict[str, Any]:
    try:
        provider = DataProvider(use_cache=use_cache)
        stock_data_obj = provider.fetch_stock_data(symbol)

        if not stock_data_obj:
            return {
                "symbol": symbol,
                "halal": {
                    "status": "ERROR",
                    "is_halal": False,
                    "ratios": {},
                    "checks": {},
                    "violations": ["Failed to retrieve company data from external provider."],
                    "notes": [],
                    "data_completeness": 0.0,
                },
            }

        stock_dict = dataclasses.asdict(stock_data_obj)
        engine = HalalEngine()
        result_dict = engine.evaluate(stock_dict)

        return result_dict.get("halal", {})

    except Exception as e:
        logger.error("Halal Pipeline failed for %s: %s", symbol, str(e))
        return {
            "symbol": symbol,
            "halal": {
                "status": "ERROR",
                "is_halal": False,
                "ratios": {},
                "checks": {},
                "violations": [f"Internal pipeline failure: {str(e)}"],
                "notes": [],
                "data_completeness": 0.0,
            },
        }
