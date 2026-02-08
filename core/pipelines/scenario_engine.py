"""
Baseline probabilistic scenario engine.

W5 deliverable:
- Load historical OHLCV
- Compute returns
- Fit baseline distribution
- Run Monte Carlo simulations
"""

from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class ScenarioConfig:
    asset: str
    horizon_days: int
    n_scenarios: int = 10_000


class ScenarioEngine:

    def __init__(self, price_df: pd.DataFrame):
        """
        price_df must contain:
        - date
        - close
        """
        self.price_df = price_df.copy()


#===============================================
#           compute_returns
#===============================================
     
    def compute_returns(self) -> pd.Series:
        """
        Compute daily log-returns from historical close prices.

        Steps:
        - Normalize column names and sort by date.
        - Convert prices to numeric values.
        - Compute log returns: r_t = ln(P_t / P_{t-1}).
        - Remove NaN and infinite values.

        Returns
        -------
        pd.Series
            Cleaned time series of daily log-returns, indexed in time order.

        Notes
        -----
        Log-returns are used because they are additive over time
        and are commonly assumed to follow a stationary distribution
        in financial modeling and Monte Carlo simulations.
        """
         
        df = self.price_df.copy()

        # basic validation
        required_cols = {"date", "close"}
        missing = required_cols - set(df.columns.str.lower())
        if missing:
            raise ValueError(f"price_df must contain columns: {required_cols}")

        # normalize column names (in case CSV has Date, Close, etc.)
        df.columns = [c.lower() for c in df.columns]

        # date to datetime, sort
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # ensure numeric close
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

        # compute log returns
        # r_t = ln(close_t / close_{t-1})
        close = df["close"]
        log_ret = np.log(close / close.shift(1))

        # drop NaN and infinities
        log_ret = log_ret.replace([np.inf, -np.inf], np.nan).dropna()

        log_ret.name = "log_return"
        return log_ret

#===============================================
#               fit_distribution
#===============================================

    def fit_distribution(self, returns: pd.Series) -> dict:
        """
        Fit a baseline probabilistic model to historical returns.

        This W5 baseline implementation fits a Normal distribution
        to the empirical log-return series and estimates:

        - mu    : mean daily return
        - sigma : standard deviation (volatility)

        Parameters
        ----------
        returns : pd.Series
            Time series of daily log-returns.

        Returns
        -------
        dict
            Dictionary containing distribution parameters, e.g.:

            {
                "dist": "normal",
                "mu": float,
                "sigma": float,
                "n": int
            }

        Notes
        -----
        This is intentionally simple and serves as a starting point.
        More advanced models (Student-t, GARCH, regime switching)
        can be added later in future milestones.
        """
         
        if returns is None or len(returns) < 30:
            raise ValueError("returns series is too short to fit a distribution")

        r = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(r) < 30:
            raise ValueError("returns series has insufficient valid values after cleaning")

        mu = float(r.mean())
        sigma = float(r.std(ddof=1))  # sample std

        if sigma <= 0:
            raise ValueError("sigma is not positive, cannot fit Normal distribution")

        return {
            "dist": "normal",
            "mu": mu,
            "sigma": sigma,
            "n": int(len(r)),
        }

    

#===============================================
#       Monte Carlo simulation of price paths
#===============================================

    def simulate_paths(self, params: dict, start_price: float, horizon_days: int, n_scenarios: int):
        """
        Run Monte Carlo simulation of future price paths using
        a geometric Brownian motion with normally distributed returns.

        Parameters
        ----------
        params : dict
            Output of fit_distribution(), must contain mu and sigma.
        start_price : float
            Last observed asset price.
        horizon_days : int
            Number of days to simulate into the future.
        n_scenarios : int
            Number of simulated paths.

        Returns
        -------
        np.ndarray
            Array of shape (n_scenarios, horizon_days + 1)
            containing simulated price paths.
        """

        mu = params["mu"]
        sigma = params["sigma"]

        if start_price <= 0:
            raise ValueError("start_price must be positive")

        dt = 1.0  # daily step

        # draw random shocks
        shocks = np.random.normal(
            loc=mu * dt,
            scale=sigma * np.sqrt(dt),
            size=(n_scenarios, horizon_days),
        )

        # cumulative log returns
        cum_returns = np.cumsum(shocks, axis=1)

        # price paths: P_t = P0 * exp(sum r_t)
        paths = start_price * np.exp(cum_returns)

        # prepend starting price at t=0
        start_col = np.full((n_scenarios, 1), start_price)
        paths = np.concatenate([start_col, paths], axis=1)

        return paths

    
#===============================================
#             run and create output
#===============================================

    def run(self, config: ScenarioConfig) -> dict:
        """
        End-to-end baseline scenario generation.

        Pipeline:
        1) compute log returns
        2) fit Normal distribution params (mu, sigma)
        3) simulate Monte Carlo price paths
        4) compute summary statistics on terminal prices

        Returns a dict that can later be consumed by an agent or API layer.
        """
        df = self.price_df.copy()
        df.columns = [c.lower() for c in df.columns]

        # last observed price (starting point)
        last_price = float(pd.to_numeric(df["close"], errors="coerce").dropna().iloc[-1])

        returns = self.compute_returns()
        params = self.fit_distribution(returns)

        paths = self.simulate_paths(
            params=params,
            start_price=last_price,
            horizon_days=config.horizon_days,
            n_scenarios=config.n_scenarios,
        )

        terminal = paths[:, -1]

        summary = {
            "start_price": last_price,
            "horizon_days": int(config.horizon_days),
            "n_scenarios": int(config.n_scenarios),
            "terminal_mean": float(np.mean(terminal)),
            "terminal_median": float(np.median(terminal)),
            "terminal_p05": float(np.percentile(terminal, 5)),
            "terminal_p50": float(np.percentile(terminal, 50)),
            "terminal_p95": float(np.percentile(terminal, 95)),
        }

        return {
            "asset": config.asset,
            "distribution": params,
            "summary": summary,
            "paths": paths,  # for now keep full paths (later can be optional)
    }

