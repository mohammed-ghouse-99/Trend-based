from dataclasses import dataclass, field
from typing import List

@dataclass
class ShariahRulesConfig:
    """
    Configurable parameters for business and financial screening.
    Based on general AAOIFI standards.
    """
    # Financial screening thresholds
    max_debt_ratio: float = 0.33             # Total Debt / Market Cap < 33%
    max_interest_income_ratio: float = 0.05  # Interest Income / Total Revenue < 5%
    max_liquidity_ratio: float = 0.50        # (Cash + Receivables) / Total Assets < 50%
    
    # Qualitative (Business) keyword blacklist
    prohibited_keywords: List[str] = field(default_factory=lambda: [
        "alcohol", "wine", "brewery", "distillery", "liquor",
        "gambling", "casino", "betting", "lottery",
        "tobacco", "cigarette",
        "pork", "swine", "haram",
        "adult", "pornography", "adult entertainment",
        "arms", "weapons", "defense contractor",  # Often subjective, but standard in ESG/Halal combinations
        "interest", "conventional bank", "insurance", "hedge fund", "brokerage"
    ])
    
    # Sectors generally flagged for secondary manual review or direct rejection
    high_risk_sectors: List[str] = field(default_factory=lambda: [
        "Financial Services", 
        "Banks",
        "Insurance",
        "Capital Markets",
        "Consumer Services"  # Often contains casinos/gambling, requires deeper NLP check
    ])

# Default standard instance
DEFAULT_RULES = ShariahRulesConfig()
