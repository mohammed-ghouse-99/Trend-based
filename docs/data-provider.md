# Data Provider Architecture

## Overview

The data provider layer provides a clean, modular, production-ready abstraction over financial data sources. It follows a provider-factory-fallback pattern:

```
Application
    |
    v
FinancialService (entry point with caching)
    |
    v
ProviderFactory (routing + fallback)
    |
    +---> FMPProvider (primary)
    |
    +---> YahooProvider (fallback)
    |
    v
FinancialData (normalized output)
```

## Architecture

### Layers

1. **FinancialService** - High-level entry point used by the application. Handles caching (15-minute TTL), delegates to ProviderFactory, and returns normalized `FinancialData`.

2. **ProviderFactory** - Manages provider registration, determines which provider is primary (FMP if API key is present) and which is fallback (Yahoo Finance). Implements automatic fallback: if primary fails, fallback is called transparently.

3. **FMPProvider** - Implements `BaseProvider` for Financial Modeling Prep v3 API. Handles all FMP-specific error cases.

4. **YahooProvider** - Implements `BaseProvider` for Yahoo Finance via `yfinance`. Always available as a fallback.

5. **BaseProvider** - Abstract base class defining the provider interface.

### Provider Flow

```
1. Caller requests data via FinancialService.get_financial_data("AAPL")
2. FinancialService checks in-memory + disk cache (15 min TTL)
3. If cache miss, delegates to ProviderFactory.fetch_with_fallback()
4. Factory tries FMPProvider first
5. If FMP succeeds -> return FinancialData
6. If FMP fails (error, timeout, empty, rate limit) -> try YahooProvider
7. If Yahoo succeeds -> return FinancialData
8. If both fail -> return None
9. FinancialService caches result and returns
```

## Files

```
project/
    data/
        providers/
            __init__.py           # Public exports
            base.py               # FinancialData dataclass + BaseProvider ABC
            fmp_provider.py       # Financial Modeling Prep implementation
            yahoo_provider.py     # Yahoo Finance (yfinance) implementation
            provider_factory.py   # Factory with automatic fallback
            financial_service.py  # Entry point with caching
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `FMP_API_KEY` | No | None | Financial Modeling Prep API key. If missing, FMP is disabled and Yahoo Finance is used directly. |

### Key Validation

- If `FMP_API_KEY` is missing or empty:
  - FMP provider is disabled
  - A warning is logged: "FMP_API_KEY not found"
  - The system automatically uses Yahoo Finance
  - No crash occurs
- If `FMP_API_KEY` is invalid:
  - FMP returns an auth error
  - System automatically falls back to Yahoo Finance
  - Error is logged

## Normalized Data Model

All providers return the same `FinancialData` structure:

| Field | Type | Description |
|---|---|---|
| `symbol` | `str` | Ticker symbol (uppercase) |
| `company_name` | `str` | Full company name |
| `market_cap` | `Optional[float]` | Market capitalization |
| `sector` | `str` | Company sector |
| `industry` | `str` | Company industry |
| `description` | `str` | Business description |
| `total_assets` | `Optional[float]` | Total assets |
| `total_debt` | `Optional[float]` | Total debt |
| `cash` | `Optional[float]` | Cash and equivalents |
| `receivables` | `Optional[float]` | Net receivables |
| `revenue` | `Optional[float]` | Total revenue |
| `operating_income` | `Optional[float]` | Operating income |
| `interest_expense` | `Optional[float]` | Interest expense |
| `interest_income` | `Optional[float]` | Interest income |
| `current_assets` | `Optional[float]` | Current assets |
| `current_liabilities` | `Optional[float]` | Current liabilities |
| `shares_outstanding` | `Optional[float]` | Shares outstanding |
| `currency` | `str` | Reporting currency (default USD) |
| `fiscal_year` | `Optional[int]` | Fiscal year of report |
| `last_updated` | `Optional[str]` | ISO timestamp of fetch |

### Conversion Methods

- `to_dict()` - Returns all fields as snake_case dict
- `to_halal_dict()` - Returns camelCase dict for HalalEngine (`marketCap`, `totalDebt`, etc.)

## Error Handling

All provider errors are caught and logged. The system never exposes Python tracebacks to users.

| Scenario | Behavior |
|---|---|
| Invalid API Key | ProviderAuthError raised -> fallback to Yahoo |
| Network failure | ProviderError raised -> fallback to Yahoo |
| Timeout | ProviderTimeoutError raised -> fallback to Yahoo |
| Rate limit | ProviderRateLimitError raised -> fallback to Yahoo |
| Empty response | Logged as warning -> fallback to Yahoo |
| Invalid ticker | Returns None -> caller gets graceful error |

## Logging

Structured logging with clear provider attribution:

```
INFO     Using Financial Modeling Prep for AAPL
INFO     FMP returned data for AAPL
WARNING  FMP returned empty response for INVALID
ERROR    FMP timeout for AAPL: Connection timed out
ERROR    FMP invalid API key: Invalid API KEY!
WARNING  Falling back to Yahoo Finance for AAPL
INFO     Yahoo Finance returned data for AAPL
ERROR    All providers failed for INVALID
WARNING  FMP_API_KEY not found. FMP provider disabled.
```

## Caching

- Two-tier: in-memory dict + JSON file on disk
- TTL: 15 minutes (900 seconds)
- Cache directory: `project_cache/financial/`
- Cache key: uppercase symbol (e.g., `AAPL.json`)
- Cache file includes `_metadata` with `cached_at` timestamp
- `clear_cache(symbol)` clears single entry
- `clear_cache()` clears all entries

## Adding a New Provider

To add a new data provider (e.g., Alpha Vantage, Finnhub, Polygon):

1. Create a new file `project/data/providers/new_provider.py`
2. Implement the `BaseProvider` abstract class:

```python
from project.data.providers.base import BaseProvider, FinancialData

class NewProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "New Provider"

    def is_available(self) -> bool:
        return True  # Check API key, connectivity, etc.

    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        # Fetch and map to FinancialData
        ...

    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        ...

    # Implement all other abstract methods
```

3. Register in `ProviderFactory._initialize_providers()`:

```python
self._providers["new_provider"] = NewProvider()
```

4. Update `get_primary_provider()` if this should be the new primary.

No changes to the Halal Engine, pipeline, or dashboard are needed.

## Testing

### Running Tests

```bash
python test_providers.py
```

### Test Coverage

| Test | Description |
|---|---|
| `TestFinancialData` | Model serialization, halal dict conversion |
| `TestFMPProvider` | Successful requests, empty responses, error handling, interest fallback |
| `TestFMPProvider.test_request_auth_error` | Invalid API key raises ProviderAuthError |
| `TestFMPProvider.test_request_timeout` | Timeout raises ProviderTimeoutError |
| `TestFMPProvider.test_request_rate_limit` | Rate limit raises ProviderRateLimitError |
| `TestFMPProvider.test_request_network_error` | Network failure raises ProviderError |
| `TestYahooProvider` | Basic provider properties |
| `TestProviderFactory` | Factory initialization with/without FMP key |
| `TestProviderFactoryFallback` | FMP failure triggers Yahoo fallback, both fail, FMP success skips fallback |
| `TestFinancialService` | Service integration with mocked provider |
| `TestFinancialServiceCaching` | Cache write, read, single clear, global clear |

## Deployment

### Render

No special configuration needed. Set `FMP_API_KEY` as an environment variable in the Render dashboard.

```bash
# In Render environment variables:
FMP_API_KEY=your_fmp_api_key
```

### Vercel

Set `FMP_API_KEY` in Vercel project settings:

```bash
vercel env add FMP_API_KEY
```

For serverless functions, the cache directory uses `/tmp/project_cache` automatically (handled by `storage.py`).

## Troubleshooting

**Q: FMP is not being used even though I set the API key.**
A: Verify the key is set and accessible: `echo $FMP_API_KEY`. Check the logs for "FMP_API_KEY found".

**Q: Yahoo Finance is slow.**
A: Yahoo Finance is the fallback. Enable FMP with a valid API key for faster responses. Enable caching (`use_cache=True`) to reduce repeated calls.

**Q: Getting "FMP rate limit reached".**
A: Free FMP tier has limits. The system will automatically fall back to Yahoo Finance. Upgrade your FMP plan or reduce request frequency.

**Q: Data seems stale.**
A: Cache TTL is 15 minutes. Force a fresh fetch by clearing cache: `from project.data.providers.financial_service import FinancialService; FinancialService().clear_cache("AAPL")`.

## Future Providers

The provider layer is designed for extensibility. Candidate providers:

| Provider | Priority | Status |
|---|---|---|
| Financial Modeling Prep | Primary | Implemented |
| Yahoo Finance | Fallback | Implemented |
| Alpha Vantage | Future | Not implemented |
| Finnhub | Future | Not implemented |
| Polygon.io | Future | Not implemented |
| Twelve Data | Future | Not implemented |
| Tiingo | Future | Not implemented |
| IEX Cloud | Future | Not implemented |

To add any of these, follow the "Adding a New Provider" section above. No changes to the Halal Engine are required.
