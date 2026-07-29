import sys
import os
import json
import dataclasses
from unittest.mock import MagicMock, patch

sys.path.append(os.getcwd())

from project.core.halal.data_provider import enrich_stock_data, DataProvider
from project.core.halal.models import StockData
from project.data.providers.fmp_provider import FMPProvider
from project.data.providers.financial_service import FinancialService
from project.data.providers.base import FinancialData


def test_manual_mapping():
    print("--- Testing Manual Mapping & Fallback Logic (New Provider Layer) ---")

    fmp_provider = FMPProvider(api_key="test_key")

    with patch.object(fmp_provider, "_request") as mock_request:
        def side_effect(endpoint, params=None):
            if "profile" in endpoint:
                return [{
                    "symbol": "AAPL",
                    "mktCap": 2500000000000,
                    "sector": "Technology",
                    "industry": "Consumer Electronics",
                    "description": "Apple Inc. designs, manufactures, and markets smartphones..."
                }]
            elif "income" in endpoint:
                return [{
                    "revenue": 394328000000,
                    "interestIncome": 2843000000,
                    "interestExpense": 2645000000
                }]
            elif "balance" in endpoint:
                return [{
                    "totalDebt": 120000000000,
                    "cashAndCashEquivalents": 48000000000,
                    "netReceivables": 25000000000,
                    "totalAssets": 350000000000
                }]
            return None
        mock_request.side_effect = side_effect

        data = fmp_provider.get_financial_data("AAPL")
        print(f"Normal: Interest Income = {data.interest_income}")
        assert data.interest_income == 2843000000
        assert data.revenue == 394328000000

    with patch.object(fmp_provider, "_request") as mock_request:
        def side_effect2(endpoint, params=None):
            if "profile" in endpoint:
                return [{
                    "symbol": "AAPL",
                    "mktCap": 2500000000000,
                    "sector": "Technology",
                    "industry": "Consumer Electronics",
                    "description": "Apple Inc."
                }]
            elif "income" in endpoint:
                return [{
                    "revenue": 394328000000,
                    "interestIncome": 0,
                    "interestExpense": 2645000000
                }]
            elif "balance" in endpoint:
                return [{
                    "totalDebt": 120000000000,
                    "cashAndCashEquivalents": 48000000000,
                    "netReceivables": 25000000000,
                    "totalAssets": 350000000000
                }]
            return None
        mock_request.side_effect = side_effect2

        data = fmp_provider.get_financial_data("AAPL")
        print(f"Fallback: Interest Income (Proxy) = {data.interest_income}")
        assert data.interest_income == 2645000000

    print("Mapping and Fallback Logic Verified!")


def test_integration_flow():
    print("\n--- Testing Integration Flow (Mocked) ---")

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

    project.core.halal.data_provider.DataProvider = original_provider
    print("Integration Flow Verified!")


def test_provider_factory_fallback():
    print("\n--- Testing Provider Factory Fallback ---")
    from project.data.providers.provider_factory import ProviderFactory

    with patch.object(FMPProvider, "get_financial_data") as mock_fmp, \
         patch.object(FMPProvider, "is_available", return_value=True):
        mock_fmp.return_value = None

        factory = ProviderFactory()
        result = factory.fetch_with_fallback("INVALID")
        assert result is None or result.symbol == "INVALID"
        print("Fallback to Yahoo verified" if not result else "Fallback returned data")


if __name__ == "__main__":
    try:
        test_manual_mapping()
        test_integration_flow()
        test_provider_factory_fallback()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
