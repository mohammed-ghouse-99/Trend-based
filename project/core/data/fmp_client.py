import os
import requests
import logging
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class FMPClient:
    """
    Client for Financial Modeling Prep (FMP) API.
    Provides structured methods to fetch financial statements and company profiles.
    """
    
    BASE_URL = "https://financialmodelingprep.com/stable"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            logger.warning("FMP_API_KEY not found in environment. API calls will fail.")

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[List[Dict[str, Any]]]:
        """Internal GET helper with error handling."""
        if not self.api_key:
            return None
            
        url = f"{self.BASE_URL}/{endpoint}"
        query_params = {"apikey": self.api_key}
        if params:
            query_params.update(params)
            
        try:
            response = requests.get(url, params=query_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # FMP returns an error message in a dict sometimes instead of 4xx
            if isinstance(data, dict) and "Error Message" in data:
                logger.error(f"FMP API Error: {data['Error Message']}")
                return None
                
            return data
        except Exception as e:
            logger.error(f"Failed to fetch from FMP ({endpoint}): {e}")
            return None

    def fetch_income_statement(self, symbol: str, limit: int = 1) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical income statements."""
        return self._get(f"income-statement?symbol={symbol.upper()}&limit={limit}")

    def fetch_balance_sheet(self, symbol: str, limit: int = 1) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical balance sheet statements."""
        return self._get(f"balance-sheet-statement?symbol={symbol.upper()}&limit={limit}")

    def fetch_profile(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch company profile (description, sector, industry, mktCap)."""
        return self._get(f"profile?symbol={symbol.upper()}")
