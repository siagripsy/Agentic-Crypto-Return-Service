متن# Module Responsibilities and Boundaries (W5)

This document defines the responsibilities and boundaries for each top level module in this repository.

Repository structure:
- `api/`
- `core/`
- `data/` (`raw/`, `processed/`)
- `docs/`
- `notebooks/`
- `tests/`

---

## 1) api

**Purpose**
- Expose the project capabilities through HTTP endpoints.
- Handle request and response formatting, validation, and error mapping.

**Inputs**
- HTTP requests (JSON payloads, query params).
- Auth context (if added later).

**Outputs**
- HTTP responses (JSON), status codes.
- API level error messages.

**Non responsibilities**
- No business logic, no agent orchestration logic.
- No direct data processing or feature engineering.
- No model training or heavy computation beyond calling `core`.

---

## 2) core

**Purpose**
- Contain all business logic and orchestration for the system.
- Implement the agent workflow, calling data and model components as needed.
- Provide a clean service layer for `api` to call.

**Inputs**
- Validated inputs from `api` (symbols, horizon, user constraints, etc.).
- Datasets/features from `data` access utilities.
- Model configuration and parameters.

**Outputs**
- Domain objects (analysis results), structured outputs for the API layer.
- Logs and internal metrics (optional).

**Non responsibilities**
- No web framework code (FastAPI routing, request parsing).
- No direct dependency on notebooks.
- No storing raw datasets directly, and no long term persistence logic inside business functions unless explicitly designed.

---

## 3) data

**Purpose**
- Provide the data layout and rules for data storage used by the project.
- Support reproducible data preparation steps and access patterns.

**Inputs**
- External market data sources (later), local files, or downloaded datasets.
- Raw input files placed into `data/raw/`.

**Outputs**
- Cleaned and transformed datasets placed into `data/processed/`.
- Data artifacts used by `core` (tables, feature sets, parquet/csv files).

**Non responsibilities**
- No API routing, no HTTP logic.
- No agent reasoning logic (belongs in `core`).

**Notes on pipelines**
- If the data pipeline is implemented as code, keep the orchestration in `core` and store the resulting artifacts in `data/processed/`.
- If you later add dedicated pipeline scripts, they can live under `core/pipelines/` (or a similar folder) but should always read from `data/raw/` and write to `data/processed/`.

---

## 4) notebooks

**Purpose**
- Exploration, experimentation, and quick validation (EDA, prototype code, charts).
- Demonstrate results and help the team iterate during development.

**Inputs**
- Any accessible dataset (preferably from `data/processed/`).
- Prototype code and temporary experiments.

**Outputs**
- Plots, insights, prototype results.
- Optional exported artifacts saved into `data/processed/` if needed.

**Non responsibilities**
- Notebooks should not be the only place where core functionality exists.
- Production logic must be moved into `core` once validated.

---

## 5) tests

**Purpose**
- Automated tests for correctness and regression prevention.
- Prioritize unit tests for `core` because it holds the business logic.

**Inputs**
- Test fixtures (small datasets, mocked dependencies).
- Calls to `core` services and (optionally) API test client later.

**Outputs**
- Pass/fail test results.
- Coverage signals for the team.

**Non responsibilities**
- No experimental notebooks here.
- Avoid dependence on large external datasets.

---

## Guiding principles

- `api` depends on `core`, and `core` may depend on `data` utilities and artifacts.
- Avoid circular dependencies.
- Keep interfaces simple: `api` calls a small set of `core` service functions.
- Data artifacts should be reproducible and stored under `data/processed/`.

## Core Internal Architecture

This section defines the internal architecture of `core/` as a set of submodules with clear responsibilities and interfaces. Folder names below are proposed conventions.

### core/agents

Purpose:
- Orchestrate the end to end workflow for an analysis request by coordinating data, models, scenario generation, and risk logic.

Inputs:
- `AnalysisRequest` (from `core/services`)
- Access to `core/data_access`, `core/models`, `core/scenario_engine`, `core/risk`, `core/portfolio`

Outputs:
- `AnalysisResult` (structured object ready for API serialization)

Owned by:
- Agent / Orchestration owner (Sia)

---

### core/models

Purpose:
- Provide a consistent interface to predictive/statistical components used in the system (forecasting, return distribution estimation, regime classification, etc.).

Inputs:
- Feature sets (from `core/data_access`)
- `ModelConfig` (hyperparameters, horizons, symbols)

Outputs:
- `ModelOutput` objects (predictions, probabilities, distribution parameters, uncertainty estimates)

Owned by:
- Modeling owner (team)

---

### core/data_access

Purpose:
- Read and write curated data artifacts.
- Provide schema consistent datasets and feature sets to the rest of `core`.

Inputs:
- Symbol list, date ranges, horizon settings
- Paths to `data/raw/` and `data/processed/`

Outputs:
- DataFrames / tables / feature matrices with documented schema
- Metadata (data coverage, missingness summary)

Owned by:
- Data owner (team)

---

### core/pipelines

Purpose:
- Define reproducible steps to build processed datasets and features from raw inputs.

Inputs:
- Raw datasets from `data/raw/`
- Pipeline configuration (symbols, sampling frequency, lookback windows)

Outputs:
- Processed datasets written to `data/processed/`
- Feature artifacts and pipeline logs

Owned by:
- Data engineering owner (team)

---

### core/regime_detection

Purpose:
- Detect market regimes (e.g., bull/bear/sideways, volatility clusters) used to condition return scenarios.

Inputs:
- Historical price/return features from `core/data_access`
- Optional model outputs from `core/models`

Outputs:
- `RegimeLabel` / `RegimeState` (current regime + probabilities)
- Regime timeline annotations for the lookback period

Owned by:
- Modeling owner (team)

---

### core/scenario_engine

Purpose:
- Generate probabilistic return scenarios and distributions conditioned on horizon and regime.

Inputs:
- Regime state (from `core/regime_detection`)
- Historical/statistical parameters (from `core/models` or computed features)
- Scenario configuration (num scenarios, horizon, confidence levels)

Outputs:
- `ScenarioSet` (samples, distribution summaries, quantiles, expected returns)
- Scenario metadata (assumptions, conditioning info)

Owned by:
- Modeling / Quant owner (team)

---

### core/risk

Purpose:
- Compute risk metrics and diagnostics on scenario outputs.

Inputs:
- `ScenarioSet` (from `core/scenario_engine`)
- Risk configuration (VaR/CVaR levels, max drawdown window, stress settings)

Outputs:
- `RiskReport` (VaR, CVaR, drawdown, tail risk, stress results)

Owned by:
- Risk owner (team)

---

### core/portfolio

Purpose:
- Portfolio level aggregation and allocation logic (optional if the scope includes multi asset recommendations).

Inputs:
- Per asset `ScenarioSet` and `RiskReport`
- Portfolio constraints (weights, max exposure, rebalancing rule)

Outputs:
- `PortfolioResult` (portfolio distribution, risk metrics, suggested weights if applicable)

Owned by:
- Portfolio owner (team)

---

### core/services

Purpose:
- Provide a small, stable service layer that the `api/` module calls.
- Translate API level inputs into domain requests and return domain results.

Inputs:
- Validated request payload from `api` (symbols, horizon, config options)

Outputs:
- `AnalysisResult` (domain object) or structured error types
- No framework specific objects should leak out (no FastAPI request/response types)

Owned by:
- Integration owner (Sia)


## End to End System Flow

This section describes the execution path from an external API request to the final response returned to the client.

1) API receives an analysis request.
   - Endpoint: `/analyze`
   - Payload includes symbols, horizon, confidence level, and optional portfolio constraints.

2) API validates the request and forwards it to `core/services`.

3) `core/services` builds an `AnalysisRequest` domain object and calls the main agent entrypoint:
   - `core/agents.run_analysis(request)`

4) The agent orchestrates the workflow:
   - Calls `core/data_access` to load historical price data and feature sets.
   - If needed, triggers `core/pipelines` to materialize missing processed datasets.
   - Calls `core/regime_detection` to infer the current market regime.
   - Calls `core/models` to estimate conditional parameters.
   - Calls `core/scenario_engine` to generate probabilistic return scenarios.
   - Calls `core/risk` to compute risk metrics.
   - Optionally calls `core/portfolio` for multi asset aggregation.

5) The agent aggregates all outputs into a single `AnalysisResult` object.

6) `core/services` returns the `AnalysisResult` to the API layer.

7) API serializes the result to JSON and returns an HTTP response.

---

### Failure and Retry Rules

- Data access failures propagate as typed domain errors (e.g., `DataNotAvailableError`).
- Model failures propagate as `ModelExecutionError`.
- The agent may implement retry logic for transient data fetch or compute errors.
- All failures are converted into HTTP safe error responses in the API layer.

---

### Determinism and Reproducibility

- Scenario generation must support seeded random generators.
- Every run records configuration and data version metadata.
- Pipeline outputs should be versioned inside `data/processed/`.


## Module Interfaces and Data Contracts

This section defines the minimal set of request and response contracts that connect `api` to `core`, and connect internal `core` submodules together. These are logical contracts and can be implemented later as Pydantic models (API layer) and Python dataclasses (core layer).

### Core Service Interface (API -> core/services)

#### AnalysisRequest
Purpose:
- Single source of truth for an analysis run.

Fields:
- request_id: string (uuid)
- symbols: list[string] (e.g., ["BTC", "ETH"])
- base_currency: string (e.g., "USD")
- horizon_days: int (e.g., 210)
- as_of_date: string (ISO date, optional)
- confidence_levels: list[float] (e.g., [0.90, 0.95, 0.99])
- scenario_count: int (e.g., 5000)
- seed: int (optional, for reproducibility)
- include_portfolio: bool (default false)
- portfolio_constraints: PortfolioConstraints (optional)
- options: dict (optional, advanced flags)

#### AnalysisResult
Purpose:
- Unified result returned by the agent and consumed by the API.

Fields:
- request_id: string
- symbols: list[string]
- horizon_days: int
- regime: RegimeState
- scenarios: dict[string, ScenarioSummary] (keyed by symbol)
- risk: dict[string, RiskReport] (keyed by symbol)
- portfolio: PortfolioResult (optional)
- assumptions: list[string]
- metadata: RunMetadata

Service functions:
- core/services.run_analysis(request: AnalysisRequest) -> AnalysisResult

---

### Agent Orchestration Interface (core/services -> core/agents)

Entrypoint:
- core/agents.run_analysis(request: AnalysisRequest) -> AnalysisResult

Rules:
- The agent is responsible for calling submodules in order and aggregating results.
- Submodules must not call API layer functions.

---

### Data Access Interface (core/* -> core/data_access)

#### MarketDataQuery
Fields:
- symbols: list[string]
- start_date: string (ISO date)
- end_date: string (ISO date)
- frequency: string (e.g., "1d")

#### MarketDataset
Fields:
- symbols: list[string]
- price_table_ref: string (path or identifier of processed artifact)
- returns_table_ref: string (path or identifier)
- feature_table_ref: string (path or identifier, optional)
- schema_version: string
- coverage: DataCoverage

Functions:
- core/data_access.load_market_dataset(query: MarketDataQuery) -> MarketDataset
- core/data_access.load_feature_set(query: MarketDataQuery, horizon_days: int) -> FeatureSet

---

### Pipeline Interface (optional on demand) (core/agents -> core/pipelines)

#### PipelineConfig
Fields:
- symbols: list[string]
- frequency: string
- lookback_days: int
- output_version: string (optional)

#### PipelineResult
Fields:
- processed_artifacts: list[string] (paths or identifiers)
- schema_version: string
- run_log_ref: string

Functions:
- core/pipelines.build_processed_data(config: PipelineConfig) -> PipelineResult

---

### Regime Detection Interface (core/agents -> core/regime_detection)

#### RegimeState
Fields:
- label: string (e.g., "bull", "bear", "sideways", "high_vol")
- probabilities: dict[string, float]
- as_of_date: string (ISO date)
- explanation: string (short)

Functions:
- core/regime_detection.infer_regime(features: FeatureSet) -> RegimeState

---

### Model Interface (core/agents -> core/models)

#### ModelConfig
Fields:
- horizon_days: int
- regime_label: string (optional)
- symbol: string
- parameters: dict (optional)

#### ModelOutput
Fields:
- symbol: string
- horizon_days: int
- distribution_params: dict (e.g., {"mu": ..., "sigma": ...} or mixture params)
- uncertainty: dict (optional)
- diagnostics: dict (optional)

Functions:
- core/models.estimate_distribution(features: FeatureSet, config: ModelConfig) -> ModelOutput

---

### Scenario Engine Interface (core/agents -> core/scenario_engine)

#### ScenarioConfig
Fields:
- scenario_count: int
- horizon_days: int
- seed: int (optional)
- method: string (e.g., "bootstrap", "parametric", "mixture")
- confidence_levels: list[float]

#### ScenarioSet
Fields:
- symbol: string
- horizon_days: int
- samples_ref: string (reference to stored samples if large)
- summary: ScenarioSummary
- conditioning: dict (e.g., {"regime": "...", "as_of_date": "..."})

#### ScenarioSummary
Fields:
- expected_return: float
- median_return: float
- quantiles: dict[string, float] (e.g., {"p10": ..., "p50": ..., "p90": ...})
- probability_positive: float

Functions:
- core/scenario_engine.generate_scenarios(model_output: ModelOutput, config: ScenarioConfig, regime: RegimeState) -> ScenarioSet

---

### Risk Interface (core/agents -> core/risk)

#### RiskConfig
Fields:
- confidence_levels: list[float]
- stress_mode: string (optional)

#### RiskReport
Fields:
- symbol: string
- horizon_days: int
- var: dict[string, float] (e.g., {"p95": ...})
- cvar: dict[string, float]
- max_drawdown_est: float (optional)
- tail_metrics: dict (optional)
- notes: list[string] (optional)

Functions:
- core/risk.compute_risk(scenarios: ScenarioSet, config: RiskConfig) -> RiskReport

---

### Portfolio Interface (optional) (core/agents -> core/portfolio)

#### PortfolioConstraints
Fields:
- max_positions: int (optional)
- max_weight_per_asset: float (optional)
- allow_short: bool (default false)

#### PortfolioResult
Fields:
- weights: dict[string, float]
- portfolio_scenario_summary: ScenarioSummary
- portfolio_risk: RiskReport
- notes: list[string] (optional)

Functions:
- core/portfolio.build_portfolio(scenarios: dict[string, ScenarioSet], risks: dict[string, RiskReport], constraints: PortfolioConstraints) -> PortfolioResult

---

### Run Metadata and Coverage

#### RunMetadata
Fields:
- created_at: string (ISO datetime)
- data_version: string
- code_version: string (git commit hash, optional)
- runtime_seconds: float (optional)

#### DataCoverage
Fields:
- start_date: string
- end_date: string
- missing_ratio: float
- notes: list[string]


## API Endpoints Contract (Initial)

This section defines the initial HTTP contracts exposed by `api/`. Exact implementation details may evolve, but names and payload shapes should remain stable.

### POST /analyze

Purpose:
- Run an end to end analysis for one or more symbols and return probabilistic scenario and risk summaries.

Request body (maps to `AnalysisRequest`):
- symbols: list[string]
- base_currency: string
- horizon_days: int
- as_of_date: string (optional)
- scenario_count: int
- confidence_levels: list[float]
- seed: int (optional)
- include_portfolio: bool (optional)
- portfolio_constraints: object (optional)
- options: object (optional)

Response body (maps to `AnalysisResult`):
- request_id: string
- symbols: list[string]
- horizon_days: int
- regime: object
- scenarios: object (keyed by symbol)
- risk: object (keyed by symbol)
- portfolio: object (optional)
- assumptions: list[string]
- metadata: object

Error responses:
- 400: validation error (invalid payload)
- 422: domain validation error (unsupported horizon/symbol set, invalid config combination)
- 500: internal error (unexpected failure)

---

### GET /health

Purpose:
- Simple service health check for deployment and monitoring.

Response:
- status: "ok"
- timestamp: ISO datetime (optional)

---

### GET /version (optional)

Purpose:
- Return build and run metadata useful for debugging.

Response:
- code_version: git commit hash (if available)
- data_version: string (if available)
- build_time: ISO datetime (optional)


## Global Parameter Glossary and Shared Concepts

This section defines commonly used parameters and objects that appear across modules. These definitions apply system wide.

---

### horizon_days
- Meaning: Forecast horizon in calendar days into the future.
- Used by: API, models, scenario_engine, risk.
- Notes: Must be consistent across all downstream modules in a single run.

---

### scenario_count
- Meaning: Number of Monte Carlo or bootstrap scenarios generated for a run.
- Used by: API, scenario_engine.
- Trade off: Higher values increase runtime but stabilize quantiles and tail risk metrics.

---

### confidence_levels
- Meaning: Probability thresholds used for quantile based reporting and risk metrics.
- Used by: API, scenario_engine, risk.
- Example: 0.95 corresponds to the 95% VaR / CVaR reporting level.

---

### seed
- Meaning: Random seed to make stochastic components reproducible.
- Used by: scenario_engine, models (if applicable).
- Notes: Optional but recommended for experiments and debugging.

---

### regime_label
- Meaning: Categorical market state inferred from historical behaviour.
- Examples: bull, bear, sideways, high_vol.
- Used by: regime_detection, models, scenario_engine.

---

### FeatureSet
- Meaning: Curated matrix of predictive features derived from market data.
- Produced by: data_access / pipelines.
- Consumed by: models, regime_detection.

---

### ScenarioSet
- Meaning: Collection of simulated return paths and their summary statistics for a single asset and horizon.
- Produced by: scenario_engine.
- Consumed by: risk, portfolio.

---

### distribution_params
- Meaning: Parameters describing the statistical form of the return distribution.
- Examples: mean/variance, mixture weights, regime conditioned parameters.
- Used by: models, scenario_engine.

---

### stress_mode
- Meaning: Optional flag that activates conservative or adversarial stress testing assumptions.
- Used by: risk.
- Examples: historical_crash, volatility_spike, liquidity_shock.

---

### DataCoverage
- Meaning: Metadata describing how complete the underlying dataset is.
- Fields: start_date, end_date, missing_ratio.
- Used by: data_access, RunMetadata.

---

### data_version
- Meaning: Identifier for the processed dataset snapshot used in a run.
- Used by: RunMetadata, pipelines.
- Notes: Enables reproducibility across experiments.

---

### code_version
- Meaning: Git commit hash associated with the execution.
- Used by: RunMetadata.
- Notes: Captured automatically at runtime if available.

