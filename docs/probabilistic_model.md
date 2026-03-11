#### Probabilistic Return Modeling & Risk Evaluation — Summary
1. Goal of the model
The goal of this component is to move beyond point predictions of returns and instead model the full uncertainty of future crypto returns, with a particular focus on downside risk.
Rather than predicting:
“Tomorrow’s return will be X”
we model:
“Given today’s market conditions, tomorrow’s return follows a conditional probability distribution.”
This enables:
	Value at Risk (VaR)
	Conditional Value at Risk (CVaR)
	Scenario simulation
	Risk-aware decision making (downstream allocation / agent logic)
________________________________________
2. Data & features used
Data
	Daily OHLCV data (from Yahoo Finance)
	Market-cap data (from CoinGecko)
	Note: market cap is intentionally not used as a feature in the model due to missing historical coverage and risk of bias, but is retained for downstream decision logic.
Feature engineering (inputs to the model)
All features are stationary or regime-descriptive, making them suitable for time-series ML:
	Momentum
	log_ret_1d, log_ret_5d, log_ret_10d
	Volatility
	vol_7d, vol_30d
	Risk / regime indicators
	drawdown_30d
	vol_ratio_7d_30d
	risk_adj_ret_1d
These features together encode the current market regime (calm, volatile, stressed) without explicitly labeling regimes.
________________________________________
3. Target definition
The supervised learning target is defined as:
target_log_ret_1d[t] = log_ret_1d[t + 1]
This ensures:
	No look-ahead bias
	Features at time t predict returns at time t+1
All modeling is strictly forward-looking.
________________________________________
4. Model architecture: Conditional Quantile Regression
Why quantile regression?
Traditional regression models estimate only the mean of future returns, which is insufficient for risk analysis.
Instead, we use quantile regression to estimate multiple points of the conditional return distribution:
Q_q (R_(t+1)∣X_t)

This allows us to model:
	Downside tail risk (e.g. 1%, 5% quantiles)
	Typical outcomes (median)
	Upside potential (90%, 95%, 99% quantiles)
Model choice
	GradientBoostingRegressor with loss="quantile"
	Separate model trained for each quantile
Quantiles used:
[0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
Hyperparameters (chosen for stability and generalization):
	n_estimators = 200
	learning_rate = 0.05
	max_depth = 3
This setup balances flexibility with overfitting control.
________________________________________
5. From quantiles to scenarios
The predicted quantiles form a summary of the conditional return distribution.
To generate scenarios:
	The quantile predictions are treated as points on an approximate CDF.
	Inverse-CDF sampling (via linear interpolation) is used to generate thousands of plausible future returns.
	These sampled returns are used to compute:
	VaR
	CVaR
	Scenario-based statistics
This approach avoids assuming returns are Normal and allows asymmetric, fat-tailed distributions.
________________________________________
6. Risk metrics implemented
Value at Risk (VaR)
	VaR(α): the α-quantile of the return distribution
	Interpretation:
“With probability α, returns will be worse than VaR(α).”
Conditional Value at Risk (CVaR)
	CVaR(α): average return conditional on being in the worst α% of outcomes
	Interpretation:
“If we are already in the worst α% of cases, this is the expected loss.”
CVaR is more conservative and captures tail severity, not just tail frequency.
________________________________________
7. Model evaluation methodology
Because this is a probabilistic model, evaluation focuses on calibration and distributional accuracy, not just MSE.
7.1 Pinball loss (quantile loss)
	Evaluated separately for each quantile
	Measures how well the predicted quantile matches realized outcomes
	Lower is better
7.2 Coverage (calibration)
For each quantile q, we measure:
Pr⁡(y≤Q ̂_q)

A well-calibrated model should have:
coverage ≈ q
This directly validates the correctness of VaR estimates.
________________________________________
8. Train vs test results (BTC example)
Calibration (test set)
Quantile	Target	Test coverage
0.05	5%	~4.8%
0.10	10%	~9.3%
0.50	50%	~51.8%
0.95	95%	~97.7%
0.99	99%	~99.8%
Interpretation:
	Downside quantiles (5%, 10%) are very well calibrated
	Extreme tails are slightly conservative (desirable for risk control)
	No evidence of optimistic bias
Overfitting check
	Train and test pinball losses are similar
	In many cases, test loss is slightly lower
	No degradation across quantiles
Conclusion: No signs of overfitting.
________________________________________
9. Time-series cross-validation
	Performed using TimeSeriesSplit (walk-forward validation)
	No shuffling
	Quantile pinball loss and coverage evaluated per fold
Results show:
	Stable pinball loss across folds
	Coverage remains close to target quantiles across different market regimes
This confirms the model generalizes across time.
________________________________________
10. Key conclusions
	The model successfully learns regime-conditioned return distributions
	Downside risk (VaR/CVaR) is well-calibrated and conservative
	The model generalizes across train/test splits and time
	This provides a reliable foundation for:
	Multi-month scenario simulation
	Horizon VaR/CVaR
	Risk-aware portfolio allocation
	Agentic decision logic

