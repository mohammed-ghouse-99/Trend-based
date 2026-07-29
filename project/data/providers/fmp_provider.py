import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import requests
from dotenv import load_dotenv

from project.data.providers.base import (
    BaseProvider,
    FinancialData,
    ProviderError,
    ProviderTimeoutError,
    ProviderAuthError,
    ProviderRateLimitError,
)

load_dotenv()

logger = logging.getLogger(__name__)


class FMPProvider(BaseProvider):
    STABLE_URL = "https://financialmodelingprep.com/stable"
    V3_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 15):
        raw_key = api_key or os.getenv("FMP_API_KEY") or ""
        self._api_key = raw_key.strip().strip('"').strip("'")
        self._timeout = timeout
        self._session = requests.Session()
        self._available: Optional[bool] = None

    @property
    def name(self) -> str:
        return "Financial Modeling Prep"

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if not self._api_key:
            logger.warning("FMP_API_KEY not configured. FMP provider disabled.")
            self._available = False
            return False
        try:
            # Check stable endpoint first
            resp = self._session.get(
                f"{self.STABLE_URL}/profile",
                params={"symbol": "AAPL", "apikey": self._api_key},
                timeout=self._timeout,
            )
            if resp.status_code == 200:
                self._available = True
                return True
            # Fallback to legacy v3 endpoint check
            resp_v3 = self._session.get(
                f"{self.V3_URL}/profile/AAPL",
                params={"apikey": self._api_key},
                timeout=self._timeout,
            )
            self._available = resp_v3.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[List[Dict[str, Any]]]:
        if not self._api_key:
            logger.warning("FMP_API_KEY not configured. Cannot make request to %s", endpoint)
            return None

        # Build stable URL vs v3 URL
        # endpoint e.g.: "profile" or "balance-sheet-statement"
        query_params = {"apikey": self._api_key}
        if params:
            query_params.update(params)

        # Try stable API standard first
        stable_url = f"{self.STABLE_URL}/{endpoint}"
        v3_endpoint = f"{endpoint}/{params.get('symbol')}" if params and "symbol" in params else endpoint
        v3_url = f"{self.V3_URL}/{v3_endpoint}"

        for url in [stable_url, v3_url]:
            try:
                response = self._session.get(url, params=query_params, timeout=self._timeout)
                if response.status_code == 403 or response.status_code == 404:
                    continue  # Try fallback endpoint
                response.raise_for_status()
                data = response.json()

                if isinstance(data, dict):
                    error_msg = data.get("Error Message") or data.get("error") or data.get("message")
                    if error_msg:
                        lower = error_msg.lower()
                        if "invalid" in lower and "key" in lower:
                            logger.error("FMP invalid API key: %s", error_msg)
                            raise ProviderAuthError(error_msg)
                        if "limit" in lower or "reach" in lower:
                            logger.error("FMP rate limit reached: %s", error_msg)
                            raise ProviderRateLimitError(error_msg)
                        if "legacy endpoint" in lower:
                            continue
                        logger.error("FMP API error for %s: %s", url, error_msg)
                        return None

                if isinstance(data, list) and not data:
                    logger.warning("FMP returned empty list for %s", url)
                    continue

                return data if isinstance(data, list) else [data]

            except (ProviderAuthError, ProviderRateLimitError):
                raise
            except requests.exceptions.Timeout:
                logger.error("FMP timeout for %s", url)
                continue
            except requests.exceptions.ConnectionError:
                logger.error("FMP connection error for %s", url)
                continue
            except Exception as e:
                logger.debug("FMP request failed for %s: %s", url, str(e))
                continue

        logger.warning("FMP all endpoints failed for %s", endpoint)
        return None

    def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        data = self._request("profile", {"symbol": symbol.upper()})
        if data and len(data) > 0:
            return data[0]
        return None

    def get_balance_sheet(self, symbol: str) -> Optional[Dict[str, Any]]:
        data = self._request("balance-sheet-statement", {"symbol": symbol.upper(), "limit": 1})
        if data and len(data) > 0:
            return data[0]
        return None

    def get_income_statement(self, symbol: str) -> Optional[Dict[str, Any]]:
        data = self._request("income-statement", {"symbol": symbol.upper(), "limit": 1})
        if data and len(data) > 0:
            return data[0]
        return None

    def get_cash_flow(self, symbol: str) -> Optional[Dict[str, Any]]:
        data = self._request("cash-flow-statement", {"symbol": symbol.upper(), "limit": 1})
        if data and len(data) > 0:
            return data[0]
        return None

    def get_financial_ratios(self, symbol: str) -> Optional[Dict[str, Any]]:
        data = self._request("ratios", {"symbol": symbol.upper(), "limit": 1})
        if data and len(data) > 0:
            return data[0]
        return None

    def get_market_cap(self, symbol: str) -> Optional[float]:
        profile = self.get_company_profile(symbol)
        if profile:
            val = profile.get("marketCap") or profile.get("mktCap")
            if val is not None:
                return float(val)
        ratios = self.get_financial_ratios(symbol)
        if ratios:
            val = ratios.get("marketCap") or ratios.get("mktCap")
            if val is not None:
                return float(val)
        return None

    def get_sector(self, symbol: str) -> Optional[str]:
        profile = self.get_company_profile(symbol)
        if profile:
            return profile.get("sector") or None
        return None

    def get_industry(self, symbol: str) -> Optional[str]:
        profile = self.get_company_profile(symbol)
        if profile:
            return profile.get("industry") or None
        return None

    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        symbol = symbol.upper()
        logger.info("Using FMP Provider for %s", symbol)

        profile = self.get_company_profile(symbol)
        income = self.get_income_statement(symbol)
        balance = self.get_balance_sheet(symbol)

        if not profile and not income and not balance:
            logger.warning("FMP returned no profile, income, or balance data for %s", symbol)
            return None

        p = profile or {}
        i = income or {}
        b = balance or {}

        raw_interest_inc = i.get("interestIncome")
        raw_interest_exp = i.get("interestExpense")

        interest_inc = _float(raw_interest_inc)
        interest_exp = _float(raw_interest_exp)

        # Fallback proxy for interest income
        if interest_inc is None:
            if interest_exp is not None and interest_exp > 0:
                interest_inc = interest_exp
                logger.info("FMP interest proxy used for %s: expense=%s", symbol, interest_exp)
            elif income and (i.get("revenue") is not None or i.get("operatingIncome") is not None):
                # Non-financial company with complete income statement -> interest income is 0.0
                interest_inc = 0.0

        if interest_exp is None and interest_inc is not None:
            interest_exp = 0.0

        receivables = _float(b.get("netReceivables"))
        if receivables is None and balance and b.get("totalAssets") is not None:
            receivables = 0.0

        cash = _float(b.get("cashAndCashEquivalents"))
        if cash is None:
            cash = _float(b.get("cashAndShortTermInvestments"))

        market_cap = _float(p.get("marketCap")) or _float(p.get("mktCap"))

        revenue = _float(i.get("revenue")) or _float(i.get("totalRevenue"))

        fiscal_year = None
        if i.get("date"):
            try:
                fiscal_year = int(str(i["date"]).split("-")[0])
            except (ValueError, IndexError):
                pass
        elif i.get("fiscalYear"):
            try:
                fiscal_year = int(i["fiscalYear"])
            except ValueError:
                pass

        fin_data = FinancialData(
            symbol=symbol,
            company_name=p.get("companyName") or p.get("symbol", symbol),
            market_cap=market_cap,
            sector=p.get("sector", ""),
            industry=p.get("industry", ""),
            description=p.get("description", ""),
            total_assets=_float(b.get("totalAssets")),
            total_debt=_float(b.get("totalDebt")),
            cash=cash,
            receivables=receivables,
            revenue=revenue,
            operating_income=_float(i.get("operatingIncome")),
            interest_expense=interest_exp,
            interest_income=interest_inc,
            current_assets=_float(b.get("totalCurrentAssets")),
            current_liabilities=_float(b.get("totalCurrentLiabilities")),
            shares_outstanding=_float(b.get("commonStockSharesOutstanding")),
            currency=p.get("currency", "USD"),
            fiscal_year=fiscal_year,
            last_updated=datetime.now().isoformat() if p else None,
        )

        required_metrics = [
            ("market_cap", fin_data.market_cap),
            ("total_assets", fin_data.total_assets),
            ("total_debt", fin_data.total_debt),
            ("cash", fin_data.cash),
            ("revenue", fin_data.revenue),
            ("interest_income", fin_data.interest_income),
            ("sector", fin_data.sector),
            ("industry", fin_data.industry),
            ("description", fin_data.description),
        ]
        present = [m[0] for m in required_metrics if m[1] is not None and m[1] != ""]
        missing = [m[0] for m in required_metrics if m[1] is None or m[1] == ""]

        logger.info("INFO FMP returned %d/%d required metrics for %s", len(present), len(required_metrics), symbol)
        if missing:
            logger.info("INFO FMP missing metrics for %s: %s", symbol, ", ".join(missing))

        return fin_data


def _float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
