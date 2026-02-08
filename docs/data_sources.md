# Data Sources and API Feasibility (Week 5)

## Goal
Choose a data source plan that supports reproducibility and the project scope.
We need daily historical crypto market data including price, volume, and market capitalization.

## Candidate Sources Tested
### 1) Yahoo Finance (primary for OHLCV)
- Assets tested: BTC, ETH
- BTC rows: 4163
- BTC date range: 2014-09-17 to 2026-02-08
- ETH rows: 3014
- ETH date range: 2017-11-09 to 2026-02-08

What we can reliably get:
- Daily OHLC and Volume with long history.

Known limitations:
- Yahoo does not provide long term historical CoinMarketCap style market cap via the same path we used.
- We treat Yahoo as OHLCV only.

### 2) CoinGecko (primary for Market Cap metadata, but limited in our current plan)
- Endpoint tested: market cap series
- Using Demo API key:
  - BTC market_cap coverage: 8.77 percent (about 365 days only)
  - ETH market_cap coverage: 12.11 percent (about 365 days only)

Known limitations:
- CoinGecko is a reputable source and holds long term historical data, but access to long history requires a paid API plan.
- With the Demo key, we only receive about one year of market cap data.
- This creates missing values if we need market cap features over longer horizons.

## Decision (Primary + Fallback)
Primary plan:
- OHLCV: Yahoo Finance
- Market Cap: CoinGecko (Demo key, last 1 year only)

Fallback options (if we must have long market cap history):
- Use a static dataset source (for example Kaggle export or a one time historical snapshot) and store it under data/raw with provenance notes.
- Or remove market cap dependent features from the baseline and keep market cap as optional metadata.

## Impact on Feature Engineering and Data Cleaning
- Market cap based features must handle missingness for older dates.
- Options:
  1) Compute market cap features only for the last one year window.
  2) Gate market cap features behind a flag so the pipeline works even when market cap is unavailable.

## Reproducibility Notes
- All data pulls must be rerunnable and recorded with:
  - source name
  - retrieval timestamp
  - asset list and date range
  - code version or commit hash

## API Feasibility Details

### CoinGecko Demo Plan Constraints
- Demo API key limits historical market cap access to roughly the last 365 days.
- Requests beyond this horizon return partial coverage (BTC: ~8.8 percent, ETH: ~12.1 percent).
- Paid plans are required for full multi year market cap history (approx. 104 USD per month at time of testing).

Operational implications:
- Market cap features cannot be assumed to exist for long historical windows.
- Pipelines must tolerate missing values.
- Models that require long lookback horizons must disable market cap features or restrict training windows.

### Yahoo Finance Behaviour
- Provides long range daily OHLCV data for major assets.
- BTC coverage: 2014 to present.
- ETH coverage: 2017 to present.
- Market cap style metadata is not reliably available through the same interface.

### Rate Limits and Pagination Notes
- CoinGecko enforces request rate limits on demo plans.
- Large historical pulls require pagination or batched date ranges.
- Yahoo Finance libraries typically chunk long date ranges automatically, but failures must be retried.

Mitigation Strategy:
- Cache all raw responses under data/raw with timestamped filenames.
- Avoid repeated full history pulls during development.
- Add retry and backoff logic in ingestion scripts.
