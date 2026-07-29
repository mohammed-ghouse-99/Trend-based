import dataclasses
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ProviderError(Exception):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderAuthError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


@dataclass
class FinancialData:
    symbol: str
    company_name: str = ""
    market_cap: Optional[float] = None
    sector: str = ""
    industry: str = ""
    description: str = ""
    total_assets: Optional[float] = None
    total_debt: Optional[float] = None
    cash: Optional[float] = None
    receivables: Optional[float] = None
    revenue: Optional[float] = None
    operating_income: Optional[float] = None
    interest_expense: Optional[float] = None
    interest_income: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    shares_outstanding: Optional[float] = None
    currency: str = "USD"
    fiscal_year: Optional[int] = None
    last_updated: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    def to_halal_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "sector": self.sector,
            "industry": self.industry,
            "description": self.description,
            "business_description": self.description,
            "marketCap": self.market_cap,
            "totalDebt": self.total_debt,
            "totalRevenue": self.revenue,
            "interestIncome": self.interest_income,
            "interestExpense": self.interest_expense,
            "cash": self.cash,
            "receivables": self.receivables,
            "totalAssets": self.total_assets,
            "currentAssets": self.current_assets,
            "currentLiabilities": self.current_liabilities,
        }


class BaseProvider(ABC):
    @abstractmethod
    def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_balance_sheet(self, symbol: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_income_statement(self, symbol: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_cash_flow(self, symbol: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_financial_ratios(self, symbol: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_market_cap(self, symbol: str) -> Optional[float]:
        pass

    @abstractmethod
    def get_sector(self, symbol: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_industry(self, symbol: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
