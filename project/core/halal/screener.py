import re
from typing import Tuple, List, Dict, Optional
from project.core.halal.models import StockData, ScreenResult
from project.core.halal.rules import ShariahRulesConfig, DEFAULT_RULES
from project.core.halal.scoring import calculate_halal_score, generate_recommendation

class HalalScreener:
    """
    Core engine for determining Shariah compliance of a stock.
    Performs both qualitative (business) and quantitative (financial) screenings.
    """
    
    def __init__(self, rules: ShariahRulesConfig = DEFAULT_RULES):
        self.rules = rules

    def screen(self, stock: StockData) -> ScreenResult:
        """Evaluate a stock based on Shariah rules."""
        violations = []
        notes = []
        confidence = 1.0
        
        # 1. Qualitative (Business) Screening
        bus_violations = self._screen_business(stock)
        if bus_violations:
            violations.extend(bus_violations)
            
        # 2. Quantitative (Financial) Screening
        ratios, fin_violations, fin_notes, fin_confidence = self._screen_financials(stock)
        mutated_confidence = min(confidence, fin_confidence)
        
        if fin_violations:
            violations.extend(fin_violations)
        if fin_notes:
            notes.extend(fin_notes)
            
        # 3. Determine Final Status
        if violations:
            is_halal = False
            status = "NON_COMPLIANT"
        elif mutated_confidence < 0.8:
            is_halal = False   # Lean conservative if we are missing too much data
            status = "UNCERTAIN"
        else:
            is_halal = True
            status = "COMPLIANT"
            
        result = ScreenResult(
            symbol=stock.symbol,
            is_halal=is_halal,
            confidence=mutated_confidence,
            status=status,
            ratios=ratios,
            violations=violations,
            notes=notes
        )
        
        # 4. Score and Recommend
        result.score = calculate_halal_score(result)
        result.recommendation = generate_recommendation(result, result.score)
        
        return result

    def _screen_business(self, stock: StockData) -> List[str]:
        """
        Check sector, industry, and description for prohibited keywords.
        """
        violations = []
        
        text_corpus = f"{stock.sector} {stock.industry} {stock.business_description}".lower()
        
        # Check high-risk sectors directly
        if stock.sector and stock.sector in self.rules.high_risk_sectors:
            violations.append(f"Business Violation: Operates in high-risk sector '{stock.sector}'")
            
        for keyword in self.rules.prohibited_keywords:
            # Match whole words to avoid false positives (e.g., 'wine' inside 'swine' is fine, 
            # but we blacklist both anyway. Better to match bounds).
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_corpus):
                violations.append(f"Business Violation: Flagged for keyword '{keyword}'")
                
        # Deduplicate while preserving order
        return list(dict.fromkeys(violations))

    def _screen_financials(self, stock: StockData) -> Tuple[Dict[str, Optional[float]], List[str], List[str], float]:
        """
        Calculates ratios and checks against quantitative thresholds.
        Returns: (ratios_dict, violations, notes, confidence)
        """
        violations = []
        notes = []
        confidence = 1.0
        ratios = {
            "debt_ratio": None,
            "interest_ratio": None,
            "liquidity_ratio": None
        }

        # 1. Debt Ratio
        if stock.marketCap > 0:
            debt_ratio = stock.totalDebt / stock.marketCap
            ratios["debt_ratio"] = debt_ratio
            if debt_ratio >= self.rules.max_debt_ratio:
                violations.append(f"Financial Violation: Debt ratio {debt_ratio:.2%} exceeds threshold of {self.rules.max_debt_ratio:.2%}")
        else:
            notes.append("Market Cap missing or zero. Cannot compute Debt Ratio accurately.")
            confidence -= 0.3

        # 2. Interest Income Ratio (with fallback)
        if stock.totalRevenue > 0:
            if stock.interestIncome is not None:
                interest_ratio = stock.interestIncome / stock.totalRevenue
                ratios["interest_ratio"] = interest_ratio
            else:
                # Primary data missing, attempt fallback proxy (magnitude of Interest Expense)
                notes.append("Interest income data missing. Using estimated proxy (absolute Interest Expense).")
                confidence -= 0.2
                if stock.interestExpense is not None:
                    # Some data sources list expense as negative, so take abs()
                    interest_ratio = abs(stock.interestExpense) / stock.totalRevenue
                    ratios["interest_ratio"] = interest_ratio
                else:
                    notes.append("No interest income or expense proxy available.")
                    confidence -= 0.2
                    interest_ratio = None
            
            if interest_ratio is not None and interest_ratio >= self.rules.max_interest_income_ratio:
                violations.append(f"Financial Violation: Estimated interest ratio {interest_ratio:.2%} exceeds threshold of {self.rules.max_interest_income_ratio:.2%}")
        else:
            notes.append("Total Revenue missing or zero. Cannot compute Interest Ratio.")
            confidence -= 0.2
            
        # 3. Liquidity Ratio
        if stock.totalAssets > 0:
            liquidity_ratio = (stock.cash + stock.receivables) / stock.totalAssets
            ratios["liquidity_ratio"] = liquidity_ratio
            if liquidity_ratio >= self.rules.max_liquidity_ratio:
                violations.append(f"Financial Violation: Liquidity ratio {liquidity_ratio:.2%} exceeds threshold of {self.rules.max_liquidity_ratio:.2%}")
        else:
            notes.append("Total Assets missing or zero. Cannot compute Liquidity Ratio.")
            confidence -= 0.1

        return ratios, violations, notes, max(0.0, confidence)
