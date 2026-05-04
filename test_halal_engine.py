from project.core.halal.engine import HalalEngine
import json

def run_demonstration():
    engine = HalalEngine()
    
    test_cases = [
        {
            "id": "COMPLIANT_TECH",
            "symbol": "MSFT",
            "sector": "Technology",
            "industry": "Software—Infrastructure",
            "description": "Microsoft Corporation develops, supports, and licenses software, services, and devices.",
            "marketCap": 3000000000000,
            "totalDebt": 50000000000,
            "totalRevenue": 200000000000,
            "interestIncome": 2000000000,
            "cash": 100000000000,
            "receivables": 30000000000,
            "totalAssets": 400000000000
        },
        {
            "id": "NON_COMPLIANT_BANK",
            "symbol": "JPM",
            "sector": "Financial Services",
            "industry": "Banks—Diversified",
            "description": "JPMorgan Chase & Co. operates as a financial services company worldwide.",
            "marketCap": 500000000000,
            "totalDebt": 300000000000,
            "totalRevenue": 150000000000,
            "interestIncome": 80000000000,
            "cash": 500000000000,
            "receivables": 100000000000,
            "totalAssets": 3000000000000
        },
        {
            "id": "INSUFFICIENT_DATA",
            "symbol": "STARTUP",
            "sector": "Healthcare",
            "industry": "Biotechnology",
            "description": "A new biotech startup with incomplete financials.",
            "marketCap": 100000000,
            "totalDebt": 10000000,
            "totalRevenue": None, # Missing field
            "interestIncome": 0,
            "cash": 5000000,
            "receivables": 2000000,
            "totalAssets": 20000000
        },
        {
            "id": "NON_COMPLIANT_DEBT",
            "symbol": "DEBTCO",
            "sector": "Utilities",
            "industry": "Utilities—Regulated Electric",
            "description": "High debt utility company.",
            "marketCap": 100000000,
            "totalDebt": 50000000, # 50% Debt ratio (> 33%)
            "totalRevenue": 10000000,
            "interestIncome": 100000,
            "cash": 5000000,
            "receivables": 1000000,
            "totalAssets": 200000000
        }
    ]
    
    print("--- HALAL ENGINE DEMONSTRATION ---\n")
    for case in test_cases:
        print(f"Testing Case: {case['id']} ({case['symbol']})")
        result = engine.evaluate(case.copy())
        print(json.dumps(result["halal"], indent=2))
        print("-" * 40)

if __name__ == "__main__":
    run_demonstration()
