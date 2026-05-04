from project.core.halal.models import ScreenResult

def calculate_halal_score(result: ScreenResult) -> float:
    """
    Advanced Halal Scoring System (0-100).
    Reward clean financial structure and penalize high debt/interest exposure.
    If the stock is non-compliant based on business activities, score is 0.
    """
    if not result.is_halal and result.status == "NON_COMPLIANT":
        # Check if it was a business violation
        if any("business" in v.lower() or "sector" in v.lower() for v in result.violations):
            return 0.0

    score = 100.0

    # 1. Debt Penalty (Max 30 points)
    # Threshold is 33%. 0% debt = 0 penalty. 33% debt = -30 points. >33% = severely penalized.
    debt_ratio = result.ratios.get("debt_ratio")
    if debt_ratio is not None:
        if debt_ratio >= 0.33:
            score -= 40
        else:
            score -= (debt_ratio / 0.33) * 30

    # 2. Interest Income Penalty (Max 40 points)
    # Threshold is 5%. 0% = 0 penalty. 5% = -40 points.
    interest_ratio = result.ratios.get("interest_ratio")
    if interest_ratio is not None:
        if interest_ratio >= 0.05:
            score -= 50
        else:
            score -= (interest_ratio / 0.05) * 40

    # 3. Liquidity Penalty (Max 10 points)
    # Too much cash/receivables (threshold 50%) is penalized slightly.
    liquidity_ratio = result.ratios.get("liquidity_ratio")
    if liquidity_ratio is not None:
        if liquidity_ratio >= 0.50:
            score -= 15
        else:
            score -= (liquidity_ratio / 0.50) * 10

    # 4. Confidence Penalty
    # If data was estimated/proxied (e.g. confidence < 1.0), lower the score slightly to reflect risk
    if result.confidence < 0.9:
        score -= 5

    return max(0.0, round(score, 2))

def generate_recommendation(result: ScreenResult, score: float) -> str:
    """
    Generate a simple recommendation based on the halal status and score.
    """
    if not result.is_halal:
        return "AVOID"
    
    if result.status == "UNCERTAIN":
        return "WATCHLIST (UNCERTAIN)"
        
    if score >= 80:
        return "STRONG HALAL BUY"
    elif score >= 60:
        return "HALAL BUY"
    elif score >= 40:
        return "WATCHLIST"
    else:
        return "AVOID (WEAK FINANCIALS)"
