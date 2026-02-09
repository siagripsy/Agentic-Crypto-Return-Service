# Capstone Project Worklog _ Sia

# ✅ Week 5



<span style="color:red"><h5>
W5 -- Data Ingestion Pipeline (Daily OHLCV) + Storage Format
</h5></span>
------------------------------------------------------------------------

## 1. Objective

The objective of this task was to design and implement a **reliable,
reproducible daily OHLCV ingestion pipeline** for crypto assets that:

-   Pulls historical price and volume data from external providers.
-   Handles API limitations and partial coverage.
-   Normalizes schemas across sources.
-   Stores outputs in a consistent on-disk format for downstream
    modeling.
-   Supports backtesting and future extensions.

This pipeline is the **data backbone** of the project and feeds:

-   Scenario engine
-   ML forecasting models
-   Agent decision modules
-   API endpoints

------------------------------------------------------------------------

## 2. Context and Dependencies

This work followed:

-   Repository and branching setup.
-   Architecture and interfaces definition.
-   Data source feasibility research.

Primary external providers evaluated:

-   CoinGecko
-   Yahoo Finance

------------------------------------------------------------------------

## 3. Repository Structure Used

    root/
    ├── core/
    │   └── data_sources/
    │       ├── coingecko.py
    │       ├── yahoo.py
    │       └── base.py
    ├── core/
    │   └── pipelines/
    │       └── ingestion_pipeline.py
    ├── data/
    │   ├── raw/
    │   │   └── metadata/
    │   └── processed/
    │       └── daily/
    │           ├── BTC_daily.csv
    │           └── ETH_daily.csv
    └── notebooks/
        └── data_ingestion_demo.py

------------------------------------------------------------------------

## 4. Development Workflow

### 4.1 Feature Branch

All work was completed in:

    feature/w5-data-ingestion-pipeline

------------------------------------------------------------------------

### 4.2 Python Environment

A project-level virtual environment (`venv`) was activated to ensure
dependency consistency.

------------------------------------------------------------------------

## 5. Pipeline Architecture

The ingestion pipeline was structured into three layers:

    [API Client] --> [Normalizer] --> [Storage Writer]

Implemented inside:

    core/pipelines/ingestion_pipeline.py

------------------------------------------------------------------------

## 6. Methodology

### 6.1 Data Sources

#### Yahoo Finance

-   Long historical OHLCV coverage.
-   No API key required.
-   Stable for daily candles.

#### CoinGecko

-   Market-cap and metadata provider.
-   Rate limits on free tier.
-   Limited historical daily market-cap in API demo tier.

------------------------------------------------------------------------

### 6.2 Schema Normalization

All sources were converted into a unified schema:

  Column   Description
  -------- -----------------
  date     UTC trading day
  open     Opening price
  high     Daily high
  low      Daily low
  close    Closing price
  volume   Trading volume
  source   Provider name

------------------------------------------------------------------------

### 6.3 Handling API Constraints

Strategies implemented:

-   Automatic batching by date ranges.
-   Backoff and retry logic.
-   Graceful fallback to secondary providers.
-   Missing data left blank rather than fabricated.
-   Logging of coverage statistics.

------------------------------------------------------------------------

### 6.4 Storage Format

Processed outputs stored as:

    data/processed/daily/{ASSET}_daily.csv

Design goals:

-   Human-readable.
-   Git-ignore friendly for large datasets.
-   Easy Pandas ingestion.
-   Versionable schemas.

Metadata saved in:

    data/raw/metadata/

------------------------------------------------------------------------

## 7. Demo and Validation

A notebook/script demonstrated:

-   Pulling BTC and ETH historical candles.
-   Writing daily CSV outputs.
-   Printing coverage ranges.
-   Reporting missing fields.

Example metrics:

-   BTC coverage: 2014 → present
-   ETH coverage: 2017 → present
-   CoinGecko market-cap coverage limited to \~1 year on free tier.

------------------------------------------------------------------------

## 8. Key Design Decisions

-   Yahoo Finance selected as primary OHLCV source.
-   CoinGecko used mainly for metadata and experimental market-cap
    pulls.
-   Storage decoupled from ingestion logic.
-   Schema-first design to protect downstream modules.
-   Logging coverage for transparency.

------------------------------------------------------------------------

## 9. Limitations

Current version:

-   Relies on free-tier APIs.
-   Market-cap not fully backfilled historically.
-   No real-time streaming ingestion.
-   Manual re-runs for refreshes.

------------------------------------------------------------------------

## 10. Risk Mitigations

  Risk              Mitigation
  ----------------- -----------------------
  API outages       Multiple providers
  Rate limits       Chunked queries
  Schema drift      Central normalizer
  Missing history   Flags + documentation

------------------------------------------------------------------------

## 11. Roadmap for Future Upgrades

-   Paid API tiers for deeper history.
-   Scheduled ingestion jobs.
-   Incremental daily updates.
-   Database-backed storage.
-   Real-time WebSocket feeds.
-   Data validation checksums.

------------------------------------------------------------------------

## 12. Summary

This W5 task successfully delivered:

-   A working ingestion pipeline.
-   Multi-source support.
-   Standardized daily OHLCV storage.
-   Documented coverage gaps.
-   Reproducible demos.

This establishes the data foundation required for all subsequent
modeling and agentic layers.

------------------------------------------------------------------------



<span style="color:red"><h5>
W5  Initial Probabilistic Scenario Engine Baseline
</h5></span>
------------------------------------------------------------------------

## 1. Objective

The goal of this milestone was to design and implement the **first
working probabilistic scenario engine** for crypto assets.\
This baseline version:

-   Uses historical OHLCV price data.
-   Computes daily log‑returns.
-   Fits a simple statistical distribution.
-   Runs Monte Carlo simulations to generate thousands of possible
    future price paths.
-   Produces structured outputs ready for agent or API consumption.

This engine is **not yet machine learning based**.\
It serves as a **statistical benchmark** for future AI models.

------------------------------------------------------------------------

## 2. Project Context

This work builds on prior completed W5 tasks:

-   Data ingestion pipeline (CoinGecko / Yahoo).
-   Daily OHLCV storage in `data/processed/daily/`.
-   Architecture & module interfaces.
-   GitHub branching and PR workflow.

------------------------------------------------------------------------

## 3. Repository Structure Used

    root/
    ├── core/
    │   └── pipelines/
    │       └── scenario_engine.py
    ├── tests/
    │   └── test_scenario_engine_smoke.py
    ├── notebooks/
    │   └── demo_scenario_engine.py
    └── data/
        └── processed/
            └── daily/
                └── BTC_daily.csv

------------------------------------------------------------------------

## 4. Development Workflow

### 4.1 Feature Branch

Work was done in:

    feature/w5-scenario-engine-baseline

This allows isolated development and later merge into `dev`.

------------------------------------------------------------------------

### 4.2 Python Environment

A project‑local `venv` environment was activated before all runs to
guarantee dependency consistency.

------------------------------------------------------------------------

## 5. Scenario Engine Architecture

The core class is:

``` python
ScenarioEngine
```

Pipeline stages:

1.  `compute_returns()`
2.  `fit_distribution()`
3.  `simulate_paths()`
4.  `run()`

------------------------------------------------------------------------

## 6. Methodology

### 6.1 Log‑Returns

From close prices:

\[ r_t = `\ln `{=tex}`\left`{=tex}( `\frac{P_t}{P_{t-1}}`{=tex}
`\right`{=tex}) \]

Why log‑returns:

-   Additive over time.
-   Common in financial modeling.
-   Suitable for Monte Carlo simulation.

------------------------------------------------------------------------

### 6.2 Distribution Fitting

Baseline assumption:

-   **Normal distribution**

Estimated parameters:

-   μ (mean return)
-   σ (volatility)
-   n (number of historical observations)

------------------------------------------------------------------------

### 6.3 Monte Carlo Simulation

Thousands of random future paths are generated using:

-   Geometric Brownian Motion.
-   Random shocks drawn from the fitted distribution.

Each path represents **one possible future market scenario**.

------------------------------------------------------------------------

## 7. Demo Execution

A standalone script was added:

    notebooks/demo_scenario_engine.py

It loads BTC data, runs 30‑day simulations, and prints:

-   Distribution parameters.
-   Summary statistics.
-   Terminal price range.

------------------------------------------------------------------------

## 8. Example Output

Below is a captured example of the console output:

![W5 Scenario Engine Demo Output](w5_demo_output.png)

------------------------------------------------------------------------

## 9. Interpretation of Results

For BTC (\~2230 days of historical data):

-   Daily mean return ≈ 0.1%.
-   Daily volatility ≈ 3.2%.

30‑day horizon simulation produced:

-   Mean terminal price above current price.
-   Wide uncertainty band.
-   Downside and upside tails captured via percentiles.

------------------------------------------------------------------------

## 10. Design Decisions

-   Normal distribution chosen for interpretability.
-   Monte Carlo used to represent uncertainty instead of point
    forecasts.
-   Entire price paths returned (future versions may make this
    optional).
-   Business logic isolated from API layer.

------------------------------------------------------------------------

## 11. Current Limitations

This baseline does **not yet include**:

-   Student‑t distributions.
-   Volatility clustering (GARCH).
-   Regime detection.
-   ML or deep learning forecasting models.

------------------------------------------------------------------------

## 12. Roadmap for Future Milestones

Planned upgrades:

-   Statistical tests for normality.
-   Alternative distributions.
-   GARCH volatility models.
-   Regime‑switching systems.
-   ML forecasting models.
-   Integration into agent decision logic.
-   REST API endpoints.

------------------------------------------------------------------------

## 13. Summary

W5 successfully delivered:

-   A functioning probabilistic engine.
-   Automated tests.
-   Reproducible demo.
-   A reference baseline for all future AI upgrades.

This establishes the quantitative backbone of the project.

------------------------------------------------------------------------


<span style="color:red"><h5>
W5 Agent Decision Logic Baseline
</h5></span>
------------------------------------------------------------------------


## Risk tolerance to allocation rules

## Goal

This baseline module converts a user or system risk tolerance into
deterministic portfolio weights.

The output is a simple dictionary mapping each symbol to a weight. The
weights are non negative and sum to 1.0.

## Location in repository

-   Implementation: `core/portfolio/allocation_rules.py`
-   Unit tests: `tests/test_allocation_rules.py`

## Inputs

-   `RiskTolerance`: conservative, moderate, aggressive
-   `AssetRiskMetrics` per asset:
    -   volatility
    -   max_drawdown (negative number)
    -   expected_return
-   `AllocationConstraints` (optional):
    -   max_positions
    -   max_weight_per_asset
    -   min_weight_per_asset

## Core idea

1)  Compute a simple risk score per asset:
    -   `risk_score = volatility + abs(max_drawdown)`
2)  Convert risk tolerance to a scoring rule:
    -   conservative: favour lower risk
    -   moderate: balance expected return and risk
    -   aggressive: favour expected return while still penalizing
        extreme risk
3)  Normalize weights so they sum to 1.0
4)  Apply caps and floors and renormalize

## Example

``` python
from core.portfolio.allocation_rules import (
    AssetRiskMetrics, AllocationConstraints, RiskTolerance, allocate_weights
)

assets = [
    AssetRiskMetrics("BTC", volatility=0.40, max_drawdown=-0.55, expected_return=0.35),
    AssetRiskMetrics("ETH", volatility=0.55, max_drawdown=-0.65, expected_return=0.45),
    AssetRiskMetrics("SOL", volatility=0.85, max_drawdown=-0.80, expected_return=0.70),
]

constraints = AllocationConstraints(max_weight_per_asset=0.60)

w = allocate_weights(RiskTolerance.MODERATE, assets, constraints=constraints)
print(w)
```

## Notes

-   If constraints become infeasible, the baseline uses a best effort
    normalization so weights still sum to 1.0.
-   Future versions can add explicit cash handling and stronger
    infeasible constraint checks.


*End of W5 Worklog.*
