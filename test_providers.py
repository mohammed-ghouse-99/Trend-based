import os
import sys
import json
import time
import unittest
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from project.data.providers.base import (
    FinancialData,
    BaseProvider,
    ProviderError,
    ProviderTimeoutError,
    ProviderAuthError,
    ProviderRateLimitError,
)
from project.data.providers.fmp_provider import FMPProvider
from project.data.providers.yahoo_provider import YahooProvider
from project.data.providers.provider_factory import ProviderFactory
from project.data.providers.financial_service import FinancialService


class TestFinancialData(unittest.TestCase):
    def test_to_dict(self):
        data = FinancialData(symbol="AAPL", company_name="Apple Inc.", market_cap=2_500_000_000_000)
        d = data.to_dict()
        self.assertEqual(d["symbol"], "AAPL")
        self.assertEqual(d["company_name"], "Apple Inc.")
        self.assertEqual(d["market_cap"], 2_500_000_000_000)

    def test_to_halal_dict(self):
        data = FinancialData(
            symbol="AAPL",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=2_500_000_000_000,
            total_debt=100_000_000,
            revenue=500_000_000,
            interest_income=10_000,
            cash=50_000_000,
            receivables=10_000_000,
            total_assets=1_000_000_000,
        )
        h = data.to_halal_dict()
        self.assertEqual(h["symbol"], "AAPL")
        self.assertEqual(h["marketCap"], 2_500_000_000_000)
        self.assertEqual(h["totalDebt"], 100_000_000)
        self.assertEqual(h["totalRevenue"], 500_000_000)
        self.assertEqual(h["interestIncome"], 10_000)
        self.assertIsNone(h.get("interestExpense"))

    def test_to_halal_dict_none_fields(self):
        data = FinancialData(symbol="TEST")
        h = data.to_halal_dict()
        self.assertEqual(h["symbol"], "TEST")
        self.assertIsNone(h["marketCap"])
        self.assertIsNone(h["totalDebt"])


class TestFMPProvider(unittest.TestCase):
    def setUp(self):
        self.provider = FMPProvider(api_key="test_key")

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_get_company_profile_success(self, mock_request):
        mock_request.return_value = [{"symbol": "AAPL", "companyName": "Apple Inc.", "mktCap": 2500000000000}]
        result = self.provider.get_company_profile("AAPL")
        self.assertIsNotNone(result)
        self.assertEqual(result["symbol"], "AAPL")

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_get_company_profile_empty(self, mock_request):
        mock_request.return_value = None
        result = self.provider.get_company_profile("INVALID")
        self.assertIsNone(result)

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_get_market_cap(self, mock_request):
        mock_request.return_value = [{"symbol": "AAPL", "mktCap": 2500000000000}]
        result = self.provider.get_market_cap("AAPL")
        self.assertEqual(result, 2500000000000.0)

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_get_sector(self, mock_request):
        mock_request.return_value = [{"symbol": "AAPL", "sector": "Technology"}]
        result = self.provider.get_sector("AAPL")
        self.assertEqual(result, "Technology")

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_get_industry(self, mock_request):
        mock_request.return_value = [{"symbol": "AAPL", "industry": "Consumer Electronics"}]
        result = self.provider.get_industry("AAPL")
        self.assertEqual(result, "Consumer Electronics")

    @patch.dict(os.environ, {}, clear=True)
    def test_is_available_no_key(self):
        provider = FMPProvider(api_key=None)
        self.assertFalse(provider.is_available())

    def test_name(self):
        self.assertEqual(self.provider.name, "Financial Modeling Prep")

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_get_financial_data_success(self, mock_request):
        def side_effect(endpoint, params=None):
            if "profile" in endpoint:
                return [{"symbol": "AAPL", "companyName": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics", "mktCap": 2500000000000, "description": "Apple Inc."}]
            elif "income" in endpoint:
                return [{"revenue": 394328000000, "interestIncome": 2843000000, "interestExpense": 2645000000, "date": "2024-09-30"}]
            elif "balance" in endpoint:
                return [{"totalAssets": 350000000000, "totalDebt": 120000000000, "cashAndCashEquivalents": 48000000000, "netReceivables": 25000000000}]
            return None
        mock_request.side_effect = side_effect

        data = self.provider.get_financial_data("AAPL")
        self.assertIsNotNone(data)
        self.assertEqual(data.symbol, "AAPL")
        self.assertEqual(data.company_name, "Apple Inc.")
        self.assertEqual(data.revenue, 394328000000)
        self.assertEqual(data.interest_income, 2843000000)

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_get_financial_data_interest_fallback(self, mock_request):
        def side_effect(endpoint, params=None):
            if "profile" in endpoint:
                return [{"symbol": "AAPL", "companyName": "Apple Inc.", "sector": "Technology", "mktCap": 2500000000000, "description": ""}]
            elif "income" in endpoint:
                return [{"revenue": 394328000000, "interestIncome": 0, "interestExpense": 2645000000, "date": "2024-09-30"}]
            elif "balance" in endpoint:
                return [{"totalAssets": 350000000000, "totalDebt": 120000000000, "cashAndCashEquivalents": 48000000000, "netReceivables": 25000000000}]
            return None
        mock_request.side_effect = side_effect

        data = self.provider.get_financial_data("AAPL")
        self.assertIsNotNone(data)
        self.assertEqual(data.interest_income, 2645000000)

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_get_financial_data_no_profile(self, mock_request):
        mock_request.return_value = None
        data = self.provider.get_financial_data("INVALID")
        self.assertIsNone(data)

    @patch("project.data.providers.fmp_provider.requests.Session.get")
    def test_request_auth_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"Error Message": "Invalid API KEY!"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        provider = FMPProvider(api_key="bad_key")
        with self.assertRaises(ProviderAuthError):
            provider.get_company_profile("AAPL")

    @patch("project.data.providers.fmp_provider.requests.Session.get")
    def test_request_rate_limit(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"Error Message": "Limit Reach"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        provider = FMPProvider(api_key="test_key")
        with self.assertRaises(ProviderRateLimitError):
            provider.get_company_profile("AAPL")

    @patch("project.data.providers.fmp_provider.requests.Session.get")
    def test_request_timeout(self, mock_get):
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("Connection timed out")
        provider = FMPProvider(api_key="test_key")
        with self.assertRaises(ProviderTimeoutError):
            provider.get_company_profile("AAPL")

    @patch("project.data.providers.fmp_provider.requests.Session.get")
    def test_request_network_error(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("DNS failure")
        provider = FMPProvider(api_key="test_key")
        with self.assertRaises(ProviderError):
            provider.get_company_profile("AAPL")

    @patch("project.data.providers.fmp_provider.FMPProvider._request")
    def test_empty_response(self, mock_request):
        mock_request.return_value = None
        result = self.provider.get_balance_sheet("NODATA")
        self.assertIsNone(result)


class TestYahooProvider(unittest.TestCase):
    def setUp(self):
        self.provider = YahooProvider()

    def test_name(self):
        self.assertEqual(self.provider.name, "Yahoo Finance")

    def test_is_available(self):
        self.assertTrue(self.provider.is_available())


class TestProviderFactory(unittest.TestCase):
    @patch.dict(os.environ, {"FMP_API_KEY": "test_key"}, clear=True)
    def test_factory_with_fmp_key(self):
        factory = ProviderFactory()
        primary = factory.get_primary_provider()
        self.assertEqual(primary.name, "Financial Modeling Prep")
        fallback = factory.get_fallback_provider()
        self.assertEqual(fallback.name, "Yahoo Finance")

    @patch.dict(os.environ, {}, clear=True)
    def test_factory_without_fmp_key(self):
        factory = ProviderFactory()
        primary = factory.get_primary_provider()
        self.assertEqual(primary.name, "Yahoo Finance")
        self.assertIsNone(factory.get_provider("fmp"))

    def test_get_all_providers(self):
        factory = ProviderFactory()
        providers = factory.get_all_providers()
        self.assertGreater(len(providers), 0)


class TestFinancialService(unittest.TestCase):
    def setUp(self):
        self.service = FinancialService(use_cache=False)

    @patch("project.data.providers.provider_factory.ProviderFactory.fetch_with_fallback")
    def test_get_financial_data(self, mock_fetch):
        mock_data = FinancialData(symbol="AAPL", company_name="Apple Inc.", market_cap=2500000000000)
        mock_fetch.return_value = mock_data
        result = self.service.get_financial_data("AAPL")
        self.assertIsNotNone(result)
        self.assertEqual(result.symbol, "AAPL")
        self.assertEqual(result.company_name, "Apple Inc.")

    @patch("project.data.providers.provider_factory.ProviderFactory.fetch_with_fallback")
    def test_get_financial_data_fallback(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.service.get_financial_data("INVALID")
        self.assertIsNone(result)


class TestProviderFactoryFallback(unittest.TestCase):
    @patch("project.data.providers.fmp_provider.FMPProvider.get_financial_data")
    @patch("project.data.providers.yahoo_provider.YahooProvider.get_financial_data")
    def test_fallback_on_fmp_failure(self, mock_yahoo, mock_fmp):
        mock_fmp.return_value = None
        mock_data = FinancialData(symbol="AAPL", company_name="Apple Inc.", market_cap=2500000000000)
        mock_yahoo.return_value = mock_data

        factory = ProviderFactory()
        result = factory.fetch_with_fallback("AAPL")
        self.assertIsNotNone(result)
        self.assertEqual(result.symbol, "AAPL")

    @patch("project.data.providers.fmp_provider.FMPProvider.get_financial_data")
    @patch("project.data.providers.yahoo_provider.YahooProvider.get_financial_data")
    def test_both_providers_fail(self, mock_yahoo, mock_fmp):
        mock_fmp.return_value = None
        mock_yahoo.return_value = None

        factory = ProviderFactory()
        result = factory.fetch_with_fallback("INVALID")
        self.assertIsNone(result)

    @patch("project.data.providers.fmp_provider.FMPProvider.get_financial_data")
    @patch("project.data.providers.yahoo_provider.YahooProvider.get_financial_data")
    def test_fmp_success_no_fallback(self, mock_yahoo, mock_fmp):
        mock_data = FinancialData(symbol="AAPL", company_name="Apple Inc.", market_cap=2500000000000)
        mock_fmp.return_value = mock_data

        factory = ProviderFactory()
        result = factory.fetch_with_fallback("AAPL")
        self.assertIsNotNone(result)
        self.assertEqual(result.symbol, "AAPL")
        mock_yahoo.assert_not_called()

    @patch("project.data.providers.fmp_provider.FMPProvider.get_financial_data")
    @patch("project.data.providers.yahoo_provider.YahooProvider.get_financial_data")
    def test_fmp_exception_triggers_fallback(self, mock_yahoo, mock_fmp):
        mock_fmp.side_effect = Exception("FMP timeout")
        mock_data = FinancialData(symbol="AAPL", company_name="Apple Inc.", market_cap=2500000000000)
        mock_yahoo.return_value = mock_data

        factory = ProviderFactory()
        result = factory.fetch_with_fallback("AAPL")
        self.assertIsNotNone(result)
        self.assertEqual(result.symbol, "AAPL")


class TestFinancialServiceCaching(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "project_cache", "test_financial"
        )
        os.makedirs(self.test_dir, exist_ok=True)
        self.service = FinancialService(use_cache=True, cache_dir=self.test_dir)

    def tearDown(self):
        import shutil
        test_cache = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "project_cache", "test_financial"
        )
        if os.path.exists(test_cache):
            shutil.rmtree(test_cache)

    def test_cache_write_and_read(self):
        data = FinancialData(symbol="CACHTEST", company_name="Cache Test Inc.", market_cap=1000000)
        self.service._save_to_cache(data)

        cached = self.service._load_from_cache("CACHTEST")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.symbol, "CACHTEST")
        self.assertEqual(cached.company_name, "Cache Test Inc.")

    def test_clear_cache_single(self):
        data = FinancialData(symbol="CLEARTEST", company_name="Clear Test Inc.")
        self.service._save_to_cache(data)
        self.service.clear_cache("CLEARTEST")
        cached = self.service._load_from_cache("CLEARTEST")
        self.assertIsNone(cached)

    def test_clear_cache_all(self):
        data1 = FinancialData(symbol="CLEAR1", company_name="Clear 1")
        data2 = FinancialData(symbol="CLEAR2", company_name="Clear 2")
        self.service._save_to_cache(data1)
        self.service._save_to_cache(data2)
        self.service.clear_cache()
        self.assertIsNone(self.service._load_from_cache("CLEAR1"))
        self.assertIsNone(self.service._load_from_cache("CLEAR2"))


if __name__ == "__main__":
    unittest.main()
