import type {
  PortfolioDetail,
  RegimeMatch,
  ScenarioEngineBlock
} from "../api/types";

function percentile(sorted: number[], p: number): number {
  if (!sorted.length) return 0;
  if (sorted.length === 1) return sorted[0];
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  const weight = idx - lo;
  return sorted[lo] * (1 - weight) + sorted[hi] * weight;
}

export function transformRegimeMatches(asset: string, matches: RegimeMatch[]) {
  return matches.map((match) => ({
    ...match,
    asset,
    drawdownSize: Math.max(Math.abs(match.max_drawdown_pct) * 1200, 80)
  }));
}

export function buildTerminalReturnBoxStats(block?: ScenarioEngineBlock | null) {
  if (!block?.paths?.length || !block.summary?.start_price) return null;
  const startPrice = block.summary.start_price;
  const returns = block.paths
    .map((path) => path[path.length - 1])
    .filter((value): value is number => Number.isFinite(value))
    .map((terminal) => terminal / startPrice - 1)
    .sort((a, b) => a - b);

  if (!returns.length) return null;
  return {
    min: returns[0],
    q1: percentile(returns, 0.25),
    median: percentile(returns, 0.5),
    q3: percentile(returns, 0.75),
    max: returns[returns.length - 1]
  };
}

export function buildFanChartBands(block?: ScenarioEngineBlock | null) {
  if (!block?.paths?.length) return [];
  const horizon = block.paths[0]?.length ?? 0;
  const rows = [];

  for (let day = 0; day < horizon; day += 1) {
    const values = block.paths
      .map((path) => path[day])
      .filter((value): value is number => Number.isFinite(value))
      .sort((a, b) => a - b);

    if (!values.length) continue;
    rows.push({
      day,
      p10: percentile(values, 0.1),
      p25: percentile(values, 0.25),
      p50: percentile(values, 0.5),
      p75: percentile(values, 0.75),
      p90: percentile(values, 0.9)
    });
  }

  return rows;
}

export function transformPortfolioRiskReturn(details: PortfolioDetail[]) {
  return details.map((detail) => ({
    ...detail,
    riskMagnitude: Math.abs(detail.cvar),
    bubbleSize: Math.max(detail.weight * 1200, 80)
  }));
}
