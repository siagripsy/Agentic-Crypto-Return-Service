Feature Engineering & Data Cleaning — System Summary
1. Purpose of the Feature Engineering Layer
The goal of the feature engineering stage is to transform raw market observations (prices, volume, market cap) into meaningful, ML-ready signals that:
	capture price dynamics
	quantify risk and uncertainty
	reveal market regimes
	remain scientifically defensible and interpretable
This layer bridges raw data ingestion and downstream modeling (regime detection, probabilistic scenarios).
________________________________________
2. Input Data (Post-Ingestion)
Feature engineering operates on processed daily datasets, one per asset
Each row represents a trading day (not calendar day) and includes:
	date
	open, high, low, close
	volume
	market_cap
	ticker
These datasets are already cleaned, merged across sources (Yahoo + CoinGecko), and time-aligned.
________________________________________
3. Core Design Principles
a) Work in Returns, Not Prices
	Raw prices are non-stationary and unsuitable for ML.
	Returns describe changes, which are more stable and comparable.
b) Separate Signal from Risk
	We explicitly distinguish directional signals (returns, momentum)
	from risk context (volatility, drawdown).
c) Rolling-Window Features Are Expected
	Features that depend on historical windows naturally produce early NaNs.
	These NaNs are structural, not data quality issues.
________________________________________
4. Engineered Features (What We Built)
4.1 Return-Based Features (Signal)
log_ret_1d
	Definition:
log⁡(P_t/P_(t-1) )

	Meaning: Daily price change.
	Role: Fundamental prediction signal used by nearly all financial ML models.
log_ret_5d
	Meaning: Price change over ~1 trading week.
	Role: Short-term momentum.
log_ret_10d
	Meaning: Price change over ~2 trading weeks.
	Role: Medium-term momentum.
________________________________________
4.2 Volatility Features (Risk & Regime Indicators)
vol_7d
	Definition: Standard deviation of daily returns over the last 7 trading days.
	Meaning: Short-term market turbulence.
vol_30d
	Definition: Standard deviation of daily returns over the last 30 trading days.
	Meaning: Longer-term risk baseline.
Volatility features are central to:
	regime detection
	uncertainty-aware modeling
	scenario generation
________________________________________
4.3 Creative / High-Value Features (Differentiators)
These features elevate the system beyond basic technical indicators.
risk_adj_ret_1d
	Definition:
"log_ret_1d" /"vol_30d" 

	Meaning: “How large was today’s move relative to normal risk?”
	Why it matters:
A 2% move in calm markets ≠ a 2% move in chaotic markets.
________________________________________
vol_ratio_7d_30d
	Definition:
"vol_7d" /"vol_30d" 

	Meaning: Whether volatility is spiking or calming.
	Interpretation:
	1 → instability / regime shift
	< 1 → stabilizing market
________________________________________
drawdown_30d
	Definition:
P_t/(max⁡(P_(t-29:t)))-1

	Meaning: Distance from the recent peak.
	Role: Captures market psychology (fear, recovery, stress).
________________________________________
5. Data Cleaning Strategy (Important)
Why NaNs Exist
	Rolling-window features (volatility, drawdown, multi-day returns) cannot be computed at the start of the dataset.
	These NaNs are expected and legitimate.
What We Do
	We do not fill or interpolate values.
	We do not inject artificial data.
Instead:
Correct Cleaning Approach
	After all features are computed, we:
	drop rows with missing required features
	keep only complete, ML-ready observations
This avoids:
	data leakage
	false signals
	bias in model training
Cleaning is done once, explicitly, inside the feature engineering layer.
________________________________________
6. Final Output of Feature Engineering
Output location:
data/processed/features/{SYMBOL}_features.csv
Each row now represents a fully defined market state, including:
	price dynamics
	momentum
	short- and long-term risk
	regime-sensitive signals
This dataset is now:
	suitable for time-series ML
	safe from leakage
	interpretable
	extensible for future features or agents
________________________________________
7. Why This Matters for Modeling
Thanks to this feature design:
	Models can learn conditional behavior (returns given risk context)
	Regime detection becomes natural and explainable
	Probabilistic return modeling has meaningful inputs
	The system aligns with professional quantitative research practices
This sets a strong foundation for:
	regime-aware ML models
	scenario simulation
	agentic decision logic

