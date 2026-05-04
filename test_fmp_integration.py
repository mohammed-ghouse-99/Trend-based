import sys
import os
import json
import dataclasses
from unittest.mock import MagicMock

# Add project to path
sys.path.append(os.getcwd())

from project.core.halal.data_provider import enrich_stock_data, DataProvider
from project.core.halal.models import StockData

def test_manual_mapping():
    print("--- Testing Manual Mapping & Fallback Logic ---")
    
    # Mock data representing FMP responses
    mock_profile = [{
        "symbol": "AAPL",
        "mktCap": 2500000000000,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "description": "Apple Inc. designs, manufactures, and markets smartphones..."
    }]
    
    # Scenario A: Interest Income exists
    mock_income_a = [{
        "revenue": 394328000000,
        "interestIncome": 2843000000,
        "interestExpense": 2645000000
    }]
    
    # Scenario B: Interest Income is missing, fallback to Interest Expense
    mock_income_b = [{
        "revenue": 394328000000,
        "interestIncome": 0,
        "interestExpense": 2645000000
    }]
    
    mock_balance = [{
        "totalDebt": 120000000000,
        "cashAndCashEquivalents": 48000000000,
        "netReceivables": 25000000000,
        "totalAssets": 350000000000
    }]

    provider = DataProvider(use_cache=False)
    provider.fmp = MagicMock()
    
    # Test Scenario A
    provider.fmp.fetch_profile.return_value = mock_profile
    provider.fmp.fetch_income_statement.return_value = mock_income_a
    provider.fmp.fetch_balance_sheet.return_value = mock_balance
    
    data_a = provider._fetch_from_fmp("AAPL")
    print(f"Scenario A (Normal): Interest Income = {data_a.interestIncome}")
    assert data_a.interestIncome == 2843000000
    
    # Test Scenario B (Fallback)
    provider.fmp.fetch_income_statement.return_value = mock_income_b
    data_b = provider._fetch_from_fmp("AAPL")
    print(f"Scenario B (Fallback): Interest Income (Proxy) = {data_b.interestIncome}")
    assert data_b.interestIncome == 2645000000
    
    print("✅ Mapping and Fallback Logic Verified!")

def test_integration_flow():
    print("\n--- Testing Integration Flow (Mocked) ---")
    # This tests the enrich_stock_data wrapper
    from project.core.halal.data_provider import DataProvider
    
    # We need to patch the DataProvider inside the module
    import project.core.halal.data_provider
    original_provider = project.core.halal.data_provider.DataProvider
    
    mock_provider = MagicMock()
    mock_provider.fetch_stock_data.return_value = StockData(
        symbol="AAPL",
        sector="Technology",
        marketCap=2500000000000,
        totalDebt=100000000,
        totalRevenue=500000000,
        interestIncome=10000,
        cash=50000000,
        receivables=10000000,
        totalAssets=1000000000
    )
    
    project.core.halal.data_provider.DataProvider = lambda: mock_provider
    
    result = enrich_stock_data("AAPL")
    print(f"Result Status: {result['halal']['status']}")
    print(f"Is Halal: {result['halal']['is_halal']}")
    
    assert result["symbol"] == "AAPL"
    assert "halal" in result
    
    # Restore
    project.core.halal.data_provider.DataProvider = original_provider
    print("✅ Integration Flow Verified!")

if __name__ == "__main__":
    try:
        test_manual_mapping()
        test_integration_flow()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        sys.exit(1)
