import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import pandas as pd
from core.pipelines.scenario_engine import ScenarioEngine, ScenarioConfig


# load sample daily data
df = pd.read_csv("data/processed/daily/BTC_daily.csv")

engine = ScenarioEngine(df[["date", "close"]])

config = ScenarioConfig(asset="BTC", horizon_days=30, n_scenarios=90000)

out = engine.run(config)

print("Asset:", out["asset"])
print("Distribution:", out["distribution"])
print("Summary:", out["summary"])

# show a quick look at terminal prices
terminal = out["paths"][:, -1]
print("Terminal min / max:", float(terminal.min()), float(terminal.max()))
