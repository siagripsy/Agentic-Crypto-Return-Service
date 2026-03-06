export function pct(x: number, digits = 2) {
  if (!Number.isFinite(x)) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

export function num(x: number, digits = 4) {
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(digits);
}