import os
import logging
from typing import Dict, List, Optional, Type

from project.data.providers.base import BaseProvider, FinancialData
from project.data.providers.fmp_provider import FMPProvider
from project.data.providers.yahoo_provider import YahooProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        raw_key = os.getenv("FMP_API_KEY", "")
        fmp_enabled = bool(raw_key.strip().strip('"').strip("'"))
        if fmp_enabled:
            logger.info("FMP_API_KEY found. FMP provider enabled.")
            self._providers["fmp"] = FMPProvider()
        else:
            logger.warning("FMP_API_KEY not found. FMP provider disabled. Using Yahoo Finance as fallback.")

        self._providers["yahoo"] = YahooProvider()

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)

    def get_primary_provider(self) -> BaseProvider:
        if "fmp" in self._providers:
            return self._providers["fmp"]
        return self._providers["yahoo"]

    def get_fallback_provider(self) -> Optional[BaseProvider]:
        return self._providers.get("yahoo")

    def get_all_providers(self) -> List[BaseProvider]:
        return list(self._providers.values())

    def get_available_providers(self) -> List[BaseProvider]:
        return [p for p in self._providers.values() if p.is_available()]

    def fetch_with_fallback(self, symbol: str) -> Optional[FinancialData]:
        primary = self.get_primary_provider()
        fallback = self.get_fallback_provider()

        primary_data: Optional[FinancialData] = None

        if primary:
            try:
                logger.info("Using %s for %s", primary.name, symbol)
                primary_data = primary.get_financial_data(symbol)
                if primary_data:
                    logger.info("%s returned data for %s", primary.name, symbol)
                else:
                    logger.warning("%s returned empty response for %s", primary.name, symbol)
            except Exception as e:
                logger.error("%s failed for %s: %s", primary.name, symbol, str(e))

        if not primary_data:
            if fallback and fallback != primary:
                logger.warning("Falling back to %s for %s", fallback.name, symbol)
                try:
                    fallback_data = fallback.get_financial_data(symbol)
                    if fallback_data:
                        logger.info("%s returned data for %s", fallback.name, symbol)
                        return fallback_data
                    logger.warning("%s returned empty response for %s", fallback.name, symbol)
                except Exception as e:
                    logger.error("%s failed for %s: %s", fallback.name, symbol, str(e))
            logger.error("All providers failed for %s", symbol)
            return None

        # Check if primary_data is missing any fields and merge from fallback provider
        required_fields = [
            ("market_cap", primary_data.market_cap),
            ("total_assets", primary_data.total_assets),
            ("total_debt", primary_data.total_debt),
            ("cash", primary_data.cash),
            ("receivables", primary_data.receivables),
            ("revenue", primary_data.revenue),
            ("interest_income", primary_data.interest_income),
            ("sector", primary_data.sector),
            ("industry", primary_data.industry),
            ("description", primary_data.description),
        ]
        missing_fields = [f[0] for f in required_fields if f[1] is None or f[1] == ""]

        if missing_fields and fallback and fallback != primary:
            logger.info("INFO Missing fields in primary provider (%s): %s", primary.name, ", ".join(missing_fields))
            logger.info("INFO Fetching missing metrics from %s", fallback.name)
            try:
                fb_data = fallback.get_financial_data(symbol)
                if fb_data:
                    for field in missing_fields:
                        fb_val = getattr(fb_data, field, None)
                        if fb_val is not None and fb_val != "":
                            setattr(primary_data, field, fb_val)
                            logger.info("INFO Patched %s from %s for %s", field, fallback.name, symbol)
            except Exception as e:
                logger.warning("Fallback provider patch failed: %s", str(e))

        # Calculate completeness
        all_fields = [
            primary_data.market_cap, primary_data.total_assets, primary_data.total_debt,
            primary_data.cash, primary_data.receivables, primary_data.revenue,
            primary_data.interest_income, primary_data.sector, primary_data.industry,
            primary_data.description
        ]
        present_count = sum(1 for v in all_fields if v is not None and v != "")
        completeness_pct = round((present_count / len(all_fields)) * 100, 1)
        logger.info("INFO Final FinancialData completeness for %s: %s%%", symbol, completeness_pct)

        return primary_data
