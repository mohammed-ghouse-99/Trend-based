from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class StockData:
    """
    Standardized payload for a stock to be evaluated by the Halal Screener.
    """
    symbol: str
    sector: str = ""
    industry: str = ""
    business_description: str = ""
    
    marketCap: float = 0.0
    totalDebt: float = 0.0
    totalRevenue: float = 0.0
    
    interestIncome: Optional[float] = None
    interestExpense: Optional[float] = None  # Fallback proxy if exact income is missing
    
    cash: float = 0.0
    receivables: float = 0.0
    totalAssets: float = 0.0

@dataclass
class ScreenResult:
    """
    Structured output representing the result of a Shariah-compliance screen.
    """
    symbol: str
    is_halal: bool
    confidence: float
    status: str  # COMPLIANT, NON_COMPLIANT, or UNCERTAIN
    
    ratios: Dict[str, Optional[float]] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    score: float = 0.0  # Optional advanced 0-100 Halal score
    recommendation: str = ""  # HALAL BUY, AVOID, WATCHLIST
    
    def to_dict(self) -> dict:
        """Serialize result to dictionary for API and UI consumers."""
        return {
            "symbol": self.symbol,
            "is_halal": self.is_halal,
            "confidence": round(self.confidence, 4),
            "status": self.status,
            "score": round(self.score, 2),
            "recommendation": self.recommendation,
            "ratios": {k: round(v, 4) if v is not None else None for k, v in self.ratios.items()},
            "violations": self.violations,
            "notes": self.notes
        }
