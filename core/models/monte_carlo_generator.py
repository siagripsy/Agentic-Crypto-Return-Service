from __future__ import annotations

import numpy as np
import pandas as pd

from core.models.scenario_generator_base import BaseScenarioGenerator, ScenarioResult


class MonteCarloScenarioGenerator(BaseScenarioGenerator):
    """
    W5 baseline Monte Carlo generator.
    - Computes log returns from close prices
    - Fits Normal(mu, sigma)
    - Simulates GBM-like paths using normal shocks on log returns
    """

    def compute_returns(self, price_df: pd.DataFrame) -> pd.Series:
        df = price_df.copy()

        # normalize column names
        df.columns = [c.lower() for c in df.columns]

        required_cols = {"date", "close"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"price_df must contain columns: {required_cols}")

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        df["close"] = pd.to_numeric(df["close"], errors="coerce")

        close = df["close"]
        log_ret = np.log(close / close.shift(1))

        log_ret = log_ret.replace([np.inf, -np.inf], np.nan).dropna()
        log_ret.name = "log_return"
        return log_ret

    def fit_distribution(self, returns: pd.Series) -> dict:
        if returns is None or len(returns) < 30:
            raise ValueError("returns series is too short to fit a distribution")

        r = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(r) < 30:
            raise ValueError("returns series has insufficient valid values after cleaning")

        mu = float(r.mean())
        sigma = float(r.std(ddof=1))

        if sigma <= 0:
            raise ValueError("sigma is not positive, cannot fit Normal distribution")

        return {"dist": "normal", "mu": mu, "sigma": sigma, "n": int(len(r))}

    def simulate_paths(
        self,
        *,
        mu: float,
        sigma: float,
        start_price: float,
        horizon_days: int,
        n_scenarios: int,
        rng: np.random.Generator,
    ) -> np.ndarray:
        if start_price <= 0:
            raise ValueError("start_price must be positive")

        dt = 1.0
        shocks = rng.normal(
            loc=mu * dt,
            scale=sigma * np.sqrt(dt),
            size=(n_scenarios, horizon_days),
        )

        cum_returns = np.cumsum(shocks, axis=1)
        paths = start_price * np.exp(cum_returns)

        start_col = np.full((n_scenarios, 1), start_price)
        paths = np.concatenate([start_col, paths], axis=1)
        return paths

    def generate(
        self,
        price_df: pd.DataFrame,
        *,
        horizon_days: int,
        n_scenarios: int,
        seed: int = 42,
        **kwargs,
    ) -> ScenarioResult:
        rng = np.random.default_rng(seed)

        df = price_df.copy()
        df.columns = [c.lower() for c in df.columns]

        last_price = float(pd.to_numeric(df["close"], errors="coerce").dropna().iloc[-1])

        returns = self.compute_returns(df)
        params = self.fit_distribution(returns)

        paths = self.simulate_paths(
            mu=params["mu"],
            sigma=params["sigma"],
            start_price=last_price,
            horizon_days=horizon_days,
            n_scenarios=n_scenarios,
            rng=rng,
        )

        return ScenarioResult(
            scenarios=paths,
            metadata={
                "generator": "monte_carlo_normal",
                "distribution": params,
                "start_price": last_price,
                "horizon_days": int(horizon_days),
                "n_scenarios": int(n_scenarios),
                "seed": int(seed),
            },
        )