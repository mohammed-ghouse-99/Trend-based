import os
import json
import time
import dataclasses
import logging
from typing import Optional, Dict, Any
from project.core.halal.models import StockData
from project.core.data.fmp_client import FMPClient
import yfinance as yf
import pandas as pd

# --- CACHE CONFIG ---
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "project_cache", "halal")
CACHE_TTL = 86400  # 1 day

logger = logging.getLogger(__name__)

class DataProvider:
    """
    Fetches raw financial data and maps it to the StockData structure.
    Integrates FMP (Primary) and yfinance (Secondary) with disk caching.
    """
    
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.fmp = FMPClient()
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
                        # Pop FMP internal fields if they exist before building model
                        metadata = data.pop("_metadata", {})
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
        """
        Primary entry point for data fetching. Attempts FMP first, then falls back to cache/yfinance.
        """
        symbol = symbol.upper()
        
        if self.use_cache:
            cached = self._load_from_cache(symbol)
            if cached:
                return cached
                
        # 1. Try FMP (Financial Modeling Prep)
        fmp_data = self._fetch_from_fmp(symbol)
        if fmp_data:
            if self.use_cache:
                self._save_to_cache(fmp_data)
            return fmp_data
            
        # 2. Fallback to yfinance
        logger.warning(f"FMP failed for {symbol} (likely missing API key). Falling back to yfinance.")
        yf_data = self._fetch_from_yfinance(symbol)
        if yf_data:
            if self.use_cache:
                self._save_to_cache(yf_data)
            return yf_data

        return None

    def _fetch_from_fmp(self, symbol: str) -> Optional[StockData]:
        """Specific extraction logic for FMP endpoints."""
        profile = self.fmp.fetch_profile(symbol)
        income = self.fmp.fetch_income_statement(symbol)
        balance = self.fmp.fetch_balance_sheet(symbol)
        
        if not profile or not income or not balance:
            return None
            
        p = profile[0]
        i = income[0]
        b = balance[0]
        
        # Interest Fallback Logic
        interest_inc = i.get("interestIncome")
        interest_exp = i.get("interestExpense")
        
        # Note detection for proxy usage
        fmp_notes = []
        if interest_inc is None or interest_inc == 0:
            if interest_exp is not None and interest_exp > 0:
                interest_inc = interest_exp
                fmp_notes.append("interest proxy used")
                logger.info(f"Using interestExpense as proxy for {symbol}")
            else:
                interest_inc = None # Will cause insufficient data in engine
        
        return StockData(
            symbol=symbol,
            sector=p.get("sector", ""),
            industry=p.get("industry", ""),
            business_description=p.get("description", ""),
            marketCap=p.get("mktCap", 0.0),
            totalDebt=b.get("totalDebt", 0.0),
            totalRevenue=i.get("revenue", 0.0),
            interestIncome=interest_inc,
            interestExpense=interest_exp,
            cash=b.get("cashAndCashEquivalents", 0.0),
            receivables=b.get("netReceivables", 0.0),
            totalAssets=b.get("totalAssets", 0.0)
        )

    def _fetch_from_yfinance(self, symbol: str) -> Optional[StockData]:
        """Fetch and map financial data from yfinance for Halal Screening (Free Fallback)."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Fetch statements
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            
            if financials.empty or balance_sheet.empty:
                logger.warning(f"Financial statements missing for {symbol} in yfinance. Using info fallback.")
                return StockData(
                    symbol=symbol,
                    sector=info.get("sector", ""),
                    industry=info.get("industry", ""),
                    business_description=info.get("longBusinessSummary", ""),
                    marketCap=info.get("marketCap", 0.0),
                    totalDebt=info.get("totalDebt", 0.0),
                    totalRevenue=info.get("totalRevenue", 0.0),
                    interestIncome=None,
                    interestExpense=None,
                    cash=info.get("totalCash", 0.0),
                    receivables=0.0,
                    totalAssets=info.get("totalAssets", 0.0)
                )

            # Extract latest column
            latest_fin = financials.iloc[:, 0]
            latest_bal = balance_sheet.iloc[:, 0]
            
            def get_val(series, *keys):
                for k in keys:
                    if k in series and series[k] is not None and not pd.isna(series[k]):
                        return float(series[k])
                return 0.0

            interest_inc = latest_fin.get("Interest Income")
            if pd.isna(interest_inc): interest_inc = None
            
            interest_exp = latest_fin.get("Interest Expense")
            if pd.isna(interest_exp): interest_exp = None
            
            return StockData(
                symbol=symbol,
                sector=info.get("sector", ""),
                industry=info.get("industry", ""),
                business_description=info.get("longBusinessSummary", ""),
                marketCap=info.get("marketCap", 0.0),
                totalDebt=get_val(latest_bal, "Total Debt", "Long Term Debt"),
                totalRevenue=get_val(latest_fin, "Total Revenue", "Operating Revenue"),
                interestIncome=float(interest_inc) if interest_inc is not None else None,
                interestExpense=float(interest_exp) if interest_exp is not None else None,
                cash=get_val(latest_bal, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"),
                receivables=get_val(latest_bal, "Net Receivables", "Receivables"),
                totalAssets=get_val(latest_bal, "Total Assets")
            )
        except Exception as e:
            logger.error(f"yfinance fetch failed for {symbol}: {e}")
            return None

def enrich_stock_data(symbol: str) -> dict:
    """
    Core integration function for Halal Screening Pipeline.
    1. Fetches from FMP
    2. Normalizes
    3. Runs through HalalEngine
    """
    from project.core.halal.engine import HalalEngine
    
    provider = DataProvider()
    stock_data = provider.fetch_stock_data(symbol)
    
    if not stock_data:
        return {"symbol": symbol, "error": "Insufficient data from FMP API"}
        
    engine = HalalEngine()
    # Convert StockData to dict as expected by HalalEngine.evaluate
    stock_dict = dataclasses.asdict(stock_data)
    result_dict = engine.evaluate(stock_dict)
    
    return result_dict

