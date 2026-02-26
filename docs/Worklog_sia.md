# Capstone Project Worklog _ Sia

# ✅ Week 5




<h1 style="background-color:powderblue;">W5 -- Data Ingestion Pipeline (Daily OHLCV) + Storage Format</h1>



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



<h1 style="background-color:powderblue;">W5  Initial Probabilistic Scenario Engine Baseline</h1>



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


<h1 style="background-color:powderblue;">W5 Agent Decision Logic Baseline</h1>


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


<h1 style="background-color:powderblue;">W5 – Model Validation on Small Dataset + Sanity Checks</h1>




1. Objective

The objective of this task was to implement systematic validation and
sanity checks across the core quantitative modules developed in Week
5.

Unlike smoke tests or demo scripts, this milestone focused on:

Verifying numerical stability.

Detecting NaN / infinite value propagation.

Ensuring deterministic outputs.

Validating structural consistency of returned objects.

Confirming rule-based allocation logic behaves correctly under different risk regimes.

This step establishes confidence and reproducibility before further
refactoring and CI integration.

2. Context

This validation layer was built on top of previously completed W5
modules:

Feature Engineering (build_features_basic)

Probabilistic Scenario Engine (ScenarioEngine)

Agent Allocation Logic (allocate_weights)

The goal was to ensure all core components behave correctly in
controlled conditions before expanding the system further.

3. Repository Structure Used

root/
├── tests/
│   ├── test_w5_sanity_features.py
│   ├── test_w5_sanity_scenario_engine.py
│   └── test_w5_sanity_allocation_rules.py
├── data/
│   └── sample/
│       └── sampleData_Test_Modelsanity.csv
└── core/
    ├── features/
    ├── pipelines/
    └── portfolio/


4. Validation Methodology

Validation was performed using pytest-based deterministic unit tests.

Three levels of validation were implemented:

4.1 Feature Engineering Sanity Checks

Verified that:

Rolling return and volatility features are correctly computed.

Required columns are present.

NaN values only appear where mathematically expected.

No infinite values propagate.

Drawdown values are non-positive.

Volatility values are non-negative.

This ensures the statistical foundation feeding the scenario engine is numerically stable.

4.2 Scenario Engine Validation

The Monte Carlo engine was validated for:

Proper dictionary structure in returned output.

Correct simulation matrix dimensions.

No NaN or infinite values in simulated paths.

Quantile ordering consistency:

p05 ≤ p50 ≤ p95

Consistency between simulated terminal distribution and summary statistics.

This confirms that stochastic simulation is structurally sound and internally coherent.

4.3 Agent Allocation Logic Validation

Allocation logic was validated under multiple scenarios:

Weights sum exactly to 1.0.

No negative or invalid weights.

Respect for:

max_positions

max_weight_per_asset

min_weight_per_asset

Behavioral differentiation between:

Conservative

Moderate

Aggressive risk tolerances.

This ensures deterministic and explainable allocation behavior.

5. Key Design Decisions

Validation focused on numerical sanity, not predictive performance.

Tests use deterministic inputs to guarantee reproducibility.

No reliance on live APIs during validation.

Explicit structural assertions to protect downstream API layers.

6. Risk Mitigation Impact

This validation layer reduces the risk of:

Risk Mitigation

Silent NaN propagation Explicit assertions in tests
Allocation instability Weight sum validation
Schema mismatch Column existence checks
Monte Carlo drift errors Distribution consistency checks
Regression bugs Pytest-based coverage

7. Limitations

Current validation does not yet include:

Statistical goodness-of-fit tests.

Distribution comparison tests.

Stress testing under extreme volatility regimes.

Cross-asset portfolio interaction testing.

8. Strategic Impact

This task transforms the project from:

“Prototype with working demo”

into:

“Validated quantitative system with structural guarantees.”

It enables safe:

Refactoring (W6)

CI integration

Future ML upgrades

API stabilization

9. Summary

W5 model validation successfully delivered:

Deterministic sanity tests for core modules.

Structural and numerical integrity verification.

Stable baseline before W6 refactoring and CI setup.

This marks the transition from prototype-level confidence to system-level reliability.

Notes: Since we are short in time, and since we don't push data to github, I skipped W6 code review and branch protection and basic CI


*End of W5 Worklog.*


<h1 style="background-color:powderblue;">W7 – Enhance Probabilistic Model (Quantile ML Walk Forward + Metrics Output)</h1>


------------------------------------------------------------------------

## 1. Objective

The objective of this week was to upgrade the scenario engine from a **W5 demo baseline** into an **AI-backed probabilistic scenario engine** that:

- Trains a **per-asset quantile regression model** (one model per coin).
- Produces **multi-day forward scenarios** using a **walk-forward** (recursive) generation approach.
- Outputs **risk and performance metrics** in a format ready for agent decision-making and demo notebooks.

Key focus:
- Make scenarios **model-driven** (AI), not random Monte Carlo demo.
- Produce **interpretable risk outputs**: probability of profit, VaR, CVaR, max drawdown, plus profit vs loss breakdown.

------------------------------------------------------------------------

## 2. Context and Dependencies

This work builds on previously completed W5/W6 tasks:

- Data ingestion pipeline (daily OHLCV + market cap).
- Feature engineering outputs saved under `data/processed/features/`.
- Baseline ScenarioEngine and module interfaces.

Inputs required for W7:
- Feature files per coin (example: `BTC_features.csv`) that include:
  `ticker, close, log_ret_1d, log_ret_5d, log_ret_10d, vol_7d, vol_30d, risk_adj_ret_1d, vol_ratio_7d_30d, drawdown_30d`

------------------------------------------------------------------------

## 3. Repository Structure Used

    root/
    ├── core/
    │   ├── pipelines/
    │   │   ├── scenario_engine.py
    │   │   └── train_quantile_models.py
    │   └── models/
    │       ├── probabilistic_quantile.py
    │       ├── quantile_ml_walkforward_generator.py
    │       ├── scenario_generator_base.py
    │       └── scenario_metrics.py
    ├── data/
    │   └── processed/
    │       └── features/
    │           ├── BTC_features.csv
    │           ├── ETH_features.csv
    │           └── ...
    ├── artifacts/
    │   └── models/
    │       ├── BTC-USD/
    │       │   └── quantile_model_bundle.joblib
    │       ├── ETH-USD/
    │       │   └── quantile_model_bundle.joblib
    │       └── ...
    └── notebooks/
        └── Test_Demo.ipynb

------------------------------------------------------------------------

## 4. Development Workflow

### 4.1 Feature Branch

All work was completed in:

    w7-enhance-prob-model-sia

------------------------------------------------------------------------

### 4.2 Python Environment

Before running any training or scenario generation:

- Activate `Capstone_env` to keep a consistent dependency baseline.

------------------------------------------------------------------------

## 5. Methodology

### 5.1 Quantile ML Model (Per Asset)

We train a separate quantile model per coin using:

- `GradientBoostingRegressor(loss="quantile")`
- Multiple quantile levels, for example:
  `q_0.01, q_0.05, q_0.10, q_0.25, q_0.50, q_0.75, q_0.90, q_0.95, q_0.99`

Interpretation:
- The model predicts a **conditional distribution** of next-day returns (not a single point forecast).
- Lower quantiles represent downside tail risk.
- Higher quantiles represent upside potential.

Artifacts saved per coin:

    artifacts/models/{TICKER}/quantile_model_bundle.joblib

Example:

    artifacts/models/BTC-USD/quantile_model_bundle.joblib

------------------------------------------------------------------------

### 5.2 Scenario Generation (Walk Forward)

We generate scenarios for `horizon_days` as follows:

1) Start from the latest known close price.
2) For each forward day:
   - recompute/refresh features from the growing history
   - predict next-day quantiles using the trained model
   - sample a return from the quantile-implied distribution
   - update the synthetic price and append it to the history
3) Repeat until horizon is complete.

This produces a full price path:

- shape: `(n_scenarios, horizon_days + 1)`
- column 0 is start price
- column -1 is terminal price at horizon end

------------------------------------------------------------------------

### 5.3 Metrics (Risk + Outcome Interpretation)

From generated paths we compute:

- Probability of profit vs loss
- VaR and CVaR on the **horizon return**
- Max Drawdown distribution within the horizon
- VaR and CVaR on **max drawdown**
- Profit and loss breakdown:
  - Profit scenarios: mean profit, max profit, min profit, mean max drawdown
  - Loss scenarios: mean loss, worst loss, smallest loss

These metrics are designed to plug directly into agent allocation logic and explainability outputs.

------------------------------------------------------------------------

## 6. ScenarioEngine Output Contract (What it Returns)

`ScenarioEngine.run(config)` returns a dictionary with a stable structure:

    {
      "asset": str,
      "distribution": dict,
      "summary": dict,
      "paths": np.ndarray,
      "metadata": dict,
      "metrics": dict
    }

### 6.1 Output Fields Explained

- **asset**
  - the requested asset label from config (ex: "BTC-USD")

- **distribution**
  - generator-dependent distribution descriptor
  - for ML generators, this may store generator name and any distribution metadata

- **summary** (W5-compatible)
  - terminal distribution summary in price units
  - includes: start_price, horizon_days, n_scenarios, terminal_mean, terminal_median, terminal_p05, terminal_p50, terminal_p95

- **paths**
  - the scenario matrix with shape `(n_scenarios, horizon_days + 1)`
  - each row is one simulated future price path

- **metadata**
  - generator name, latest_date, and any generator-specific debug fields
  - used for traceability and demos

- **metrics** (W7-added)
  - key risk and outcome measures including:
    - prob_profit, prob_loss
    - horizon_return_summary (mean, median, p05, p95)
    - VaR_CVaR_horizon_return (VaR, CVaR)
    - max_drawdown_summary (mean, median, p05, p95)
    - VaR_CVaR_max_drawdown (VaR, CVaR)
    - profit_analysis (count, mean_profit, max_profit, min_profit, mean_max_drawdown)
    - loss_analysis (count, mean_loss, worst_loss, smallest_loss)

------------------------------------------------------------------------

## 7. Demo Notes

A demo notebook was prepared to show end-to-end flow:

- Load features for requested assets
- Generate walk-forward scenarios using `model_type="quantile_ml_walk_forward"`
- Print `paths` shape and sample paths
- Print and interpret `metrics`
- Plot return and max drawdown distributions (interactive plots optional)

------------------------------------------------------------------------

## 8. Summary

W7 successfully delivered:

- AI-based probabilistic modeling per coin using quantile regression.
- Walk-forward multi-day scenario generation for any horizon.
- Risk and performance metrics computed directly from scenario paths.
- Backward-compatible ScenarioEngine output with extended `metrics` for downstream agent decisions.

This completes a core “engine layer” needed before regime similarity analysis and portfolio recommendation refinement.

------------------------------------------------------------------------

<h1 style="background-color:powderblue;">W7 – Regime Detection & Historical Matching (AI Similarity Engine)</h1>


------------------------------------------------------------------------

## 1. Objective

The objective of this milestone was to implement an **AI-based regime detection and historical similarity engine** to complement the probabilistic scenario engine.

Unlike W5 Monte Carlo and W7 quantile ML forecasting, this module:

- Identifies historical market regimes similar to the current market state.
- Uses a learned latent representation instead of raw feature distance.
- Retrieves the top-N most similar historical windows.
- Evaluates forward performance of those windows over a user-defined horizon.
- Outputs interpretable probability and risk statistics.

This module provides **contextual intelligence** to the agent layer.

------------------------------------------------------------------------

## 2. Conceptual Design

The system separates:

**Training configuration (model-level parameters):**
- match_window_days
- similarity_metric
- embargo_days
- latent_dim

**Runtime query parameters (user-level inputs):**
- top_n
- horizon_days

Key architectural principle:
The similarity model must be independent from user horizon selection.
Horizon is only applied after similar regimes are identified.

------------------------------------------------------------------------

## 3. Methodology

### 3.1 Rolling Window Construction

From feature-engineered datasets:

    data/processed/features/{COIN}_features.csv

We construct rolling windows of length:

    match_window_days

Each window contains:

- log returns (1d, 5d, 10d)
- volatility metrics
- risk-adjusted return
- volatility ratio
- drawdown

Windows slide one day at a time.

------------------------------------------------------------------------

### 3.2 Autoencoder (Latent Representation Learning)

A PyTorch Autoencoder was implemented:

    core/models/regime_autoencoder.py

Architecture:

Input (W × F) → Flatten → Dense layers → Latent vector (dim=16)

Purpose:

- Learn compressed representation of market regime.
- Remove noise and redundant correlations.
- Provide geometry for similarity search.

Training loss:

- Mean Squared Error (reconstruction loss)

Artifacts saved per coin:

    artifacts/models/{TICKER}/
        ├── regime_ae.pt
        ├── regime_scaler.pkl
        └── regime_train_config.pkl

Example:

    artifacts/models/BTC-USD/regime_ae.pt

------------------------------------------------------------------------

### 3.3 Similarity Search

After encoding all windows:

- Latent embeddings are generated.
- The most recent window is used as the query regime.
- KNN search performed using:

    cosine distance

Top-N historical regimes are retrieved while excluding:

    embargo_days

This avoids trivial near-duplicate windows.

------------------------------------------------------------------------

### 3.4 Forward Evaluation

For each matched historical window:

1. Identify its forward horizon.
2. Compute:
   - Profit percentage
   - Maximum drawdown
3. Aggregate statistics across top-N windows.

Outputs include:

- Probability of profit
- Mean / max / min profit
- Mean / worst loss
- Mean / worst max drawdown

This produces a distribution-based historical analogue forecast.

------------------------------------------------------------------------

## 4. Repository Structure Used

    root/
    ├── core/
    │   └── regime_detection/
    │       ├── historical_matching.py
    │       └── regime_detection.py
    ├── core/
    │   └── models/
    │       └── regime_autoencoder.py
    ├── artifacts/
    │   └── models/
    │       ├── BTC-USD/
    │       │   ├── regime_ae.pt
    │       │   ├── regime_scaler.pkl
    │       │   └── regime_train_config.pkl
    │       └── ...
    └── notebooks/
        └── Test_Demo.ipynb

------------------------------------------------------------------------

## 5. Development Workflow

### 5.1 Feature Branch

All work was completed in:

    w7-enhance-prob-model-sia

------------------------------------------------------------------------

### 5.2 Environment

All experiments and training were executed under:

    Capstone_env

to ensure dependency stability and reproducibility.

------------------------------------------------------------------------

## 6. Key Design Decisions

- Autoencoder chosen over raw Euclidean feature distance.
- Cosine similarity used for regime comparison.
- Clear separation between training config and query config.
- Horizon is dynamic and not baked into the model.
- Artifacts stored per coin for modular scalability.
- Model retraining avoided unless explicitly forced.

------------------------------------------------------------------------

## 7. Example Output Structure

The regime engine returns:

    {
      "current_window": {...},
      "matches": [...],
      "summary": {...},
      "used_cached_model": bool
    }

Summary includes:

- n_evaluated
- prob_profit
- profit_analysis
- loss_analysis
- drawdown_analysis

------------------------------------------------------------------------

## 8. Strategic Impact

This module upgrades the system from:

“Forecast-only probabilistic engine”

to:

“Regime-aware intelligent agent”

It enables:

- Historical analogue reasoning
- Regime-conditioned risk awareness
- More informed portfolio allocation decisions
- Future integration with LLM-based explanations

------------------------------------------------------------------------

## 9. Limitations and Future Improvements

Current version:

- Single latent dimension architecture (fixed depth).
- No clustering or regime labeling yet.
- No cross-asset regime comparison.
- No statistical validation of embedding separability.

Future upgrades:

- Add clustering layer on embeddings.
- Introduce regime classification labels.
- Compare cross-asset synchronized regimes.
- Integrate with portfolio risk weighting logic.

------------------------------------------------------------------------

## 10. Summary

W7 Regime Detection successfully delivered:

- AI-based similarity learning per asset.
- Top-N historical regime retrieval.
- Forward performance evaluation over dynamic horizon.
- Scalable artifact-based architecture.

This completes the regime intelligence layer required before full agent-based portfolio orchestration.