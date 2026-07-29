import logging
from typing import Optional, Dict, Any
from datetime import datetime

import yfinance as yf
import pandas as pd

from project.data.providers.base import BaseProvider, FinancialData

logger = logging.getLogger(__name__)


class YahooProvider(BaseProvider):
    def __init__(self):
        self._available: Optional[bool] = None

    @property
    def name(self) -> str:
        return "Yahoo Finance"

    def is_available(self) -> bool:
        return True

    def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return dict(info) if info else None
        except Exception as e:
            logger.error("Yahoo profile fetch failed for %s: %s", symbol, str(e))
            return None

    def get_balance_sheet(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            ticker = yf.Ticker(symbol)
            bs = ticker.balance_sheet
            if bs is not None and not bs.empty:
                return bs.iloc[:, 0].to_dict()
            return None
        except Exception as e:
            logger.error("Yahoo balance sheet fetch failed for %s: %s", symbol, str(e))
            return None

    def get_income_statement(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            ticker = yf.Ticker(symbol)
            financials = ticker.financials
            if financials is not None and not financials.empty:
                return financials.iloc[:, 0].to_dict()
            return None
        except Exception as e:
            logger.error("Yahoo income statement fetch failed for %s: %s", symbol, str(e))
            return None

    def get_cash_flow(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            ticker = yf.Ticker(symbol)
            cf = ticker.cashflow
            if cf is not None and not cf.empty:
                return cf.iloc[:, 0].to_dict()
            return None
        except Exception as e:
            logger.error("Yahoo cash flow fetch failed for %s: %s", symbol, str(e))
            return None

    def get_financial_ratios(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            info = self.get_company_profile(symbol)
            if not info:
                return None
            return {
                "debtRatio": info.get("debtToEquity"),
                "currentRatio": info.get("currentRatio"),
                "returnOnEquity": info.get("returnOnEquity"),
                "profitMargins": info.get("profitMargins"),
                "marketCap": info.get("marketCap"),
            }
        except Exception as e:
            logger.error("Yahoo ratios fetch failed for %s: %s", symbol, str(e))
            return None

    def get_market_cap(self, symbol: str) -> Optional[float]:
        info = self.get_company_profile(symbol)
        if info:
            val = info.get("marketCap")
            if val:
                return float(val)
        return None

    def get_sector(self, symbol: str) -> Optional[str]:
        info = self.get_company_profile(symbol)
        if info:
            return info.get("sector") or None
        return None

    def get_industry(self, symbol: str) -> Optional[str]:
        info = self.get_company_profile(symbol)
        if info:
            return info.get("industry") or None
        return None

    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        symbol = symbol.upper()
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet

            p = info
            has_financials = financials is not None and not financials.empty
            has_balance = balance_sheet is not None and not balance_sheet.empty

            def get_val(series, *keys):
                if series is None:
                    return None
                for k in keys:
                    if k in series.index:
                        val = series[k]
                        if val is not None and not (isinstance(val, float) and pd.isna(val)):
                            return float(val)
                return None

            i = financials.iloc[:, 0] if has_financials else None
            b = balance_sheet.iloc[:, 0] if has_balance else None

            market_cap = _float(p.get("marketCap"))
            sector = p.get("sector", "")
            industry = p.get("industry", "")
            description = p.get("longBusinessSummary") or p.get("description", "")

            interest_inc = get_val(i, "Interest Income", "Interest Income Non Operating", "Net Interest Income", "Interest And Investment Income")
            interest_exp = get_val(i, "Interest Expense", "Interest Expense Non Operating", "Net Interest Expense")

            if interest_inc is None and interest_exp is not None and interest_exp > 0:
                interest_inc = abs(interest_exp)

            total_debt = get_val(b, "Total Debt", "Long Term Debt", "Current Debt And Capital Lease Obligation")
            cash = get_val(b, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents", "Cash Financial")
            receivables = get_val(b, "Net Receivables", "Receivables", "Accounts Receivable")
            total_assets = get_val(b, "Total Assets")
            current_assets = get_val(b, "Total Current Assets")
            current_liabilities = get_val(b, "Total Current Liabilities")
            revenue = get_val(i, "Total Revenue", "Operating Revenue")
            operating_income = get_val(i, "Operating Income")

            # Fallbacks from ticker.info
            if total_debt is None:
                total_debt = _float(p.get("totalDebt"))
            if cash is None:
                cash = _float(p.get("totalCash"))
            if total_assets is None:
                total_assets = _float(p.get("totalAssets"))
            if revenue is None:
                revenue = _float(p.get("totalRevenue"))

            # Smart defaults when company financials are present
            if has_financials and interest_inc is None:
                interest_inc = 0.0
            if has_financials and interest_exp is None:
                interest_exp = 0.0
            if has_balance and receivables is None:
                receivables = 0.0

            fin_data = FinancialData(
                symbol=symbol,
                company_name=p.get("longName") or p.get("shortName", symbol),
                market_cap=market_cap,
                sector=sector,
                industry=industry,
                description=description,
                total_assets=total_assets,
                total_debt=total_debt,
                cash=cash,
                receivables=receivables,
                revenue=revenue,
                operating_income=operating_income,
                interest_expense=interest_exp,
                interest_income=interest_inc,
                current_assets=current_assets,
                current_liabilities=current_liabilities,
                shares_outstanding=_float(p.get("sharesOutstanding")),
                currency=p.get("currency", "USD"),
                fiscal_year=p.get("fiscalYear"),
                last_updated=datetime.now().isoformat(),
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

            logger.info("INFO Yahoo returned %d/%d required metrics for %s", len(present), len(required_metrics), symbol)
            if missing:
                logger.info("INFO Yahoo missing metrics for %s: %s", symbol, ", ".join(missing))

            return fin_data

        except Exception as e:
            logger.error("Yahoo financial data fetch failed for %s: %s", symbol, str(e))
            return None


def _float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
