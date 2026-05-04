import re
from typing import Dict, List, Optional, Tuple, Any


class HalalEngine:
    """
    Deterministic Shariah-compliance engine for equities.
    Follows a 3-step screening process (Business & Financial) with strict
    error handling and auditability.
    """

    # --- CONSTANTS: Compliance Thresholds ---
    MAX_DEBT_RATIO = 0.33
    MAX_INTEREST_RATIO = 0.05
    MAX_LIQUIDITY_RATIO = 0.50

    # --- CONSTANTS: Prohibited Category Map ---
    # Used for direct sector/industry evaluation
    PROHIBITED_CATEGORIES = {
        "alcohol": ["Alcohol", "Beverages - Wineries & Distilleries", "Brewery", "Distillery"],
        "gambling": ["Gambling", "Casinos & Gaming", "Betting", "Lottery"],
        "banking_insurance": [
            "Financial Services", "Banks", "Insurance", "Capital Markets",
            "Credit Services", "Banks - Regional", "Banks - Diversified",
            "Insurance - Life", "Insurance - Property & Casualty", "Conventional Banking"
        ],
        "tobacco": ["Tobacco", "Cigarette"],
        "adult_content": ["Adult Entertainment", "Pornography"]
    }

    # --- CONSTANTS: Prohibited Keywords ---
    # Regex-based fallback for business description scanning
    PROHIBITED_KEYWORDS = [
        r"\balcohol\b", r"\balcoholic\b", r"\bwine\b", r"\bbrewery\b", r"\bdistillery\b", r"\bliquor\b",
        r"\bgambling\b", r"\bcasino\b", r"\bbetting\b", r"\blottery\b",
        r"\btobacco\b", r"\bcigarette\b",
        r"\bpork\b", r"\bswine\b", r"\bharam\b",
        r"\badult content\b", r"\bpornography\b", r"\badult entertainment\b",
        r"\bconventional bank\b", r"\bconventional insurance\b", r"\busury\b"
    ]

    def evaluate(self, stock: dict) -> dict:
        """
        Evaluate a single stock for Halal compliance.
        """
        violations = []
        reason_codes = []
        notes = []
        checks = {
            "business": "unknown",
            "debt": "unknown",
            "interest": "unknown",
            "liquidity": "unknown"
        }
        ratios = {
            "debt_ratio": None,
            "interest_ratio": None,
            "liquidity_ratio": None
        }

        # --- 1. Business Screening ---
        biz_status, biz_violations, biz_codes = self._screen_business(stock)
        checks["business"] = biz_status
        violations.extend(biz_violations)
        reason_codes.extend(biz_codes)

        # --- 2. Financial Screening (Independent) ---
        
        # A. Debt Ratio
        status, ratio, msg, code = self._check_ratio(
            stock.get("totalDebt"), stock.get("marketCap"), self.MAX_DEBT_RATIO, "Debt Ratio"
        )
        checks["debt"] = status
        ratios["debt_ratio"] = ratio
        if status == "fail":
            violations.append(msg)
            reason_codes.append(code)
        elif msg: # for notes like zero division
            notes.append(msg)

        # B. Interest Ratio
        status, ratio, msg, code = self._check_ratio(
            stock.get("interestIncome"), stock.get("totalRevenue"), self.MAX_INTEREST_RATIO, "Interest Ratio"
        )
        checks["interest"] = status
        ratios["interest_ratio"] = ratio
        if status == "fail":
            violations.append(msg)
            reason_codes.append(code)
        elif msg:
            notes.append(msg)

        # C. Liquidity Ratio
        liq_numerator = None
        if stock.get("cash") is not None and stock.get("receivables") is not None:
            liq_numerator = stock["cash"] + stock["receivables"]
        
        status, ratio, msg, code = self._check_ratio(
            liq_numerator, stock.get("totalAssets"), self.MAX_LIQUIDITY_RATIO, "Liquidity Ratio"
        )
        checks["liquidity"] = status
        ratios["liquidity_ratio"] = ratio
        if status == "fail":
            violations.append(msg)
            reason_codes.append(code)
        elif msg:
            notes.append(msg)

        # --- 3. Final Status Logic ---
        # IF any check fails → NON_COMPLIANT
        # ELSE IF all evaluated checks pass → COMPLIANT
        # ELSE → INSUFFICIENT_DATA
        
        any_fail = any(v == "fail" for v in checks.values())
        all_pass = all(v == "pass" for v in checks.values())
        
        if any_fail:
            status = "NON_COMPLIANT"
            is_halal = False
        elif all_pass:
            status = "COMPLIANT"
            is_halal = True
        else:
            status = "INSUFFICIENT_DATA"
            is_halal = False

        # --- 4. Data Completeness ---
        total_fields = 10 # marketCap, totalDebt, totalRevenue, interestIncome, cash, receivables, totalAssets, sector, industry, description
        field_keys = ["marketCap", "totalDebt", "totalRevenue", "interestIncome", "cash", "receivables", "totalAssets", "sector", "industry", "description"]
        present_count = sum(1 for k in field_keys if stock.get(k) is not None)
        completeness = round(present_count / total_fields, 2)

        # Build output payload
        stock["halal"] = {
            "status": status,
            "is_halal": is_halal,
            "ratios": ratios,
            "checks": checks,
            "violations": violations,
            "reason_codes": reason_codes,
            "notes": notes,
            "data_completeness": completeness
        }

        return stock

    def _screen_business(self, stock: dict) -> Tuple[str, List[str], List[str]]:
        """
        Business screening: Normalize -> Match -> Fallback.
        """
        sector = (stock.get("sector") or "").strip()
        industry = (stock.get("industry") or "").strip()
        desc = (stock.get("description") or "").lower()

        # Step 1 & 2: Normalize and Match against Prohibited Categories
        for cat_name, items in self.PROHIBITED_CATEGORIES.items():
            for item in items:
                if sector.lower() == item.lower() or industry.lower() == item.lower():
                    return "fail", [f"Involved in prohibited category: {cat_name.replace('_', ' ').title()}"], [f"BIZ_CAT_{cat_name.upper()}"]

        # Step 3: Fallback to keyword search in description
        if desc:
            for pattern in self.PROHIBITED_KEYWORDS:
                if re.search(pattern, desc):
                    match = re.search(pattern, desc).group()
                    return "fail", [f"Prohibited keyword detected in description: '{match}'"], ["BIZ_KEYWORD_MATCH"]
        
        # If no sector/industry info at all
        if not sector and not industry and not desc:
            return "unknown", [], []

        return "pass", [], []

    def _check_ratio(self, numerator: Optional[float], denominator: Optional[float], threshold: float, label: str) -> Tuple[str, Optional[float], Optional[str], Optional[str]]:
        """
        Perform a financial ratio check independently.
        Returns: (status, ratio, message, reason_code)
        """
        if numerator is None or denominator is None:
            return "unknown", None, None, None
        
        if denominator == 0:
            return "unknown", None, f"Calculation skipped: Denominator is zero for {label}", "ZERO_DIVISION_SKIPPED"
        
        ratio = round(numerator / denominator, 4)
        
        if ratio >= threshold:
            code = f"FIN_{label.split()[0].upper()}_EXCEEDED"
            return "fail", ratio, f"{label} exceeded: {ratio:.2%} (Limit: {threshold:.2%})", code
        
        return "pass", ratio, None, None
