export function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return NaN;
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  const a = sorted[base] ?? sorted[sorted.length - 1];
  const b = sorted[base + 1] ?? sorted[sorted.length - 1];
  return a + rest * (b - a);
}

export function histogram(values: number[], bins = 40) {
  const xs = values.filter(Number.isFinite);
  if (xs.length === 0) return { edges: [], counts: [] };

  let min = Math.min(...xs);
  let max = Math.max(...xs);
  if (min === max) {
    min -= 1e-6;
    max += 1e-6;
  }

  const step = (max - min) / bins;
  const counts = new Array(bins).fill(0);

  for (const v of xs) {
    const idx = Math.min(bins - 1, Math.max(0, Math.floor((v - min) / step)));
    counts[idx] += 1;
  }

  const edges = Array.from({ length: bins }, (_, i) => min + i * step);
  return { edges, counts, step };
}

/**
 * Build fan bands (p05, p50, p95) for a matrix paths[nScenarios][t]
 */
export function fanBands(paths: number[][], qs: [number, number, number] = [0.05, 0.5, 0.95]) {
  if (paths.length === 0) return { t: [], pLow: [], pMid: [], pHigh: [] };

  const T = paths[0].length;
  const pLow: number[] = [];
  const pMid: number[] = [];
  const pHigh: number[] = [];
  const t = Array.from({ length: T }, (_, i) => i);

  for (let k = 0; k < T; k++) {
    const col = paths.map((row) => row[k]).filter(Number.isFinite).sort((a, b) => a - b);
    pLow.push(quantile(col, qs[0]));
    pMid.push(quantile(col, qs[1]));
    pHigh.push(quantile(col, qs[2]));
  }

  return { t, pLow, pMid, pHigh };
}