import re
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


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

        # Handle alias between 'description' and 'business_description'
        if not stock.get("description") and stock.get("business_description"):
            stock["description"] = stock["business_description"]

        # --- 1. Business Screening ---
        biz_status, biz_violations, biz_codes = self._screen_business(stock)
        checks["business"] = biz_status
        violations.extend(biz_violations)
        reason_codes.extend(biz_codes)

        # --- 2. Financial Screening (Independent) ---

        # A. Debt Ratio
        debt_num = stock.get("totalDebt")
        debt_den = stock.get("marketCap")
        status, ratio, msg, code = self._check_ratio(debt_num, debt_den, self.MAX_DEBT_RATIO, "Debt Ratio")
        checks["debt"] = status
        ratios["debt_ratio"] = ratio
        if status == "fail":
            violations.append(msg)
            reason_codes.append(code)
        elif msg:
            notes.append(msg)

        # B. Interest Ratio (with proxy and intelligent fallback)
        interest_inc = stock.get("interestIncome")
        interest_exp = stock.get("interestExpense")
        total_rev = stock.get("totalRevenue")

        if interest_inc is None:
            if interest_exp is not None and interest_exp > 0:
                interest_inc = abs(interest_exp)
                notes.append("Interest income missing; proxy estimated from absolute Interest Expense.")
            elif total_rev is not None and total_rev > 0:
                interest_inc = 0.0
                notes.append("Interest income not reported; estimated as 0.0%.")

        status, ratio, msg, code = self._check_ratio(interest_inc, total_rev, self.MAX_INTEREST_RATIO, "Interest Ratio")
        checks["interest"] = status
        ratios["interest_ratio"] = ratio
        if status == "fail":
            violations.append(msg)
            reason_codes.append(code)
        elif msg:
            notes.append(msg)

        # C. Liquidity Ratio
        cash = stock.get("cash")
        receivables = stock.get("receivables")
        total_assets = stock.get("totalAssets")

        liq_numerator = None
        if cash is not None:
            if receivables is not None:
                liq_numerator = cash + receivables
            else:
                liq_numerator = cash
                notes.append("Receivables missing; liquidity ratio calculated using cash only.")

        status, ratio, msg, code = self._check_ratio(liq_numerator, total_assets, self.MAX_LIQUIDITY_RATIO, "Liquidity Ratio")
        checks["liquidity"] = status
        ratios["liquidity_ratio"] = ratio
        if status == "fail":
            violations.append(msg)
            reason_codes.append(code)
        elif msg:
            notes.append(msg)

        # --- 3. Final Status Logic ---
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

        # Identify missing metrics
        missing_metrics = []
        if stock.get("marketCap") is None: missing_metrics.append("marketCap")
        if stock.get("totalDebt") is None: missing_metrics.append("totalDebt")
        if total_rev is None: missing_metrics.append("totalRevenue")
        if interest_inc is None: missing_metrics.append("interestIncome")
        if cash is None: missing_metrics.append("cash")
        if receivables is None: missing_metrics.append("receivables")
        if total_assets is None: missing_metrics.append("totalAssets")
        if not stock.get("sector"): missing_metrics.append("sector")
        if not stock.get("industry"): missing_metrics.append("industry")
        if not stock.get("description"): missing_metrics.append("description")

        if status == "INSUFFICIENT_DATA" and missing_metrics:
            notes.append(f"Missing critical metrics: {', '.join(missing_metrics)}")

        # --- 4. Data Completeness ---
        total_fields = 10
        field_keys = ["marketCap", "totalDebt", "totalRevenue", "interestIncome", "cash", "receivables", "totalAssets", "sector", "industry", "description"]
        present_count = sum(1 for k in field_keys if stock.get(k) is not None and stock.get(k) != "")
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
            "data_completeness": completeness,
            "missing_metrics": missing_metrics
        }

        # Print financial completeness report to logs
        sym = stock.get("symbol", "UNKNOWN")
        logger.info("=== Financial Completeness Report for %s ===", sym)
        for k in field_keys:
            val = stock.get(k)
            mark = "✅" if val is not None and val != "" else "❌"
            logger.info("  %-20s %s", k, mark)
        logger.info("Completeness: %d / %d fields (%.0f%%)", present_count, total_fields, completeness * 100)
        logger.info("Status: %s", status)

        return stock

    def _screen_business(self, stock: dict) -> Tuple[str, List[str], List[str]]:
        """
        Business screening: Normalize -> Match -> Fallback.
        """
        sector = (stock.get("sector") or "").strip()
        industry = (stock.get("industry") or "").strip()
        desc = (stock.get("description") or stock.get("business_description") or "").lower()

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
            return "unknown", None, f"Calculation skipped: Missing metric for {label}", "METRIC_MISSING"

        if denominator == 0:
            return "unknown", None, f"Calculation skipped: Denominator is zero for {label}", "ZERO_DIVISION_SKIPPED"

        ratio = round(numerator / denominator, 4)

        if ratio >= threshold:
            code = f"FIN_{label.split()[0].upper()}_EXCEEDED"
            return "fail", ratio, f"{label} exceeded: {ratio:.2%} (Limit: {threshold:.2%})", code

        return "pass", ratio, None, None
