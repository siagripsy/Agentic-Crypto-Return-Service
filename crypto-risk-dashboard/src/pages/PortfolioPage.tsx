import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Card from "../components/Card";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";
import JsonPanel from "../components/JsonPanel";
import { api } from "../api/client";
import type { PortfolioEngine, PortfolioRequest, PortfolioResponse } from "../api/types";

function kpi(label: string, value: string) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}

function parseSymbols(input: string): string[] {
  return input
    .split(",")
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

function parseConfidenceLevels(input: string): number[] {
  return input
    .split(",")
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isFinite(n) && n > 0 && n < 1);
}

function pct(x: number, digits = 2) {
  if (!Number.isFinite(x)) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

function num(x: number, digits = 4) {
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(digits);
}

function WeightsBars({ weights }: { weights?: Record<string, number> | null }) {
  const entries = Object.entries(weights ?? {});
  if (!entries.length) return null;

  const maxWeight = Math.max(...entries.map(([, v]) => v), 0.0001);

  return (
    <Card title="Portfolio weights">
      <div style={{ display: "grid", gap: 12 }}>
        {entries.map(([label, value]) => (
          <div key={label} style={{ display: "grid", gap: 6 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}>
              <span>{label}</span>
              <span style={{ fontWeight: 700 }}>{pct(value)}</span>
            </div>
            <div
              style={{
                width: "100%",
                height: 12,
                background: "#eef0f4",
                borderRadius: 999,
                overflow: "hidden",
                border: "1px solid #e5e7eb"
              }}
            >
              <div
                style={{
                  width: `${(value / maxWeight) * 100}%`,
                  height: "100%",
                  background: "#111827"
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function PortfolioPage() {
  const [symbolsCsv, setSymbolsCsv] = useState("BTC, ETH");
  const [startDate, setStartDate] = useState("2025-12-01");
  const [horizonDays, setHorizonDays] = useState(30);
  const [engine, setEngine] = useState<PortfolioEngine>("walkforward_ml");
  const [nScenarios, setNScenarios] = useState(1000);
  const [confidenceLevelsCsv, setConfidenceLevelsCsv] = useState("0.95");
  const [userRiskTolerance, setUserRiskTolerance] = useState(50);
  const [topK, setTopK] = useState(5);
  const [maxWeight, setMaxWeight] = useState(0.5);
  const [minWeight, setMinWeight] = useState(0);
  const [allowCash, setAllowCash] = useState(true);
  const [includeExplanation, setIncludeExplanation] = useState(true);
  const [explanationMode, setExplanationMode] = useState<"fallback" | "llm">("fallback");

  const req: PortfolioRequest = useMemo(
    () => ({
      symbols: parseSymbols(symbolsCsv),
      start_date: startDate,
      horizon_days: horizonDays,
      engine,
      n_scenarios: nScenarios,
      seed: 42,
      confidence_levels: parseConfidenceLevels(confidenceLevelsCsv),
      user_risk_tolerance: userRiskTolerance,
      top_k: topK,
      max_weight: maxWeight,
      min_weight: minWeight,
      allow_cash: allowCash,
      timeout_seconds: 30,
      include_explanation: includeExplanation,
      explanation_mode: explanationMode
    }),
    [
      symbolsCsv,
      startDate,
      horizonDays,
      engine,
      nScenarios,
      confidenceLevelsCsv,
      userRiskTolerance,
      topK,
      maxWeight,
      minWeight,
      allowCash,
      includeExplanation,
      explanationMode
    ]
  );

  const mut = useMutation<PortfolioResponse, Error, PortfolioRequest>({
    mutationFn: (r) => api.portfolioRecommend(r)
  });

  const weights = (mut.data?.portfolio as any)?.weights ?? null;
  const portfolioExpectedReturn = Number((mut.data?.portfolio as any)?.portfolio_expected_return);
  const portfolioCvar = Number((mut.data?.portfolio as any)?.portfolio_cvar);
  const portfolioMaxDrawdown = Number((mut.data?.portfolio as any)?.portfolio_max_drawdown_est);

  return (
    <div className="dashboard-grid">
      <div className="sidebar-stack">
        <Card title="Portfolio controls">
          <div className="form-grid">
            <label className="form-group">
              Symbols (comma-separated)
              <input value={symbolsCsv} onChange={(e) => setSymbolsCsv(e.target.value)} />
            </label>

            <label className="form-group">
              Start date
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </label>

            <label className="form-group">
              Horizon days
              <input
                type="number"
                min={1}
                max={252}
                value={horizonDays}
                onChange={(e) => setHorizonDays(Number(e.target.value))}
              />
            </label>

            <label className="form-group">
              Engine
              <select value={engine} onChange={(e) => setEngine(e.target.value as PortfolioEngine)}>
                <option value="walkforward_ml">walkforward_ml</option>
                <option value="regime_similarity">regime_similarity</option>
                <option value="ensemble">ensemble</option>
              </select>
            </label>

            <label className="form-group">
              # scenarios
              <input
                type="number"
                min={100}
                max={20000}
                value={nScenarios}
                onChange={(e) => setNScenarios(Number(e.target.value))}
              />
            </label>

            <label className="form-group">
              Confidence levels (comma-separated)
              <input
                value={confidenceLevelsCsv}
                onChange={(e) => setConfidenceLevelsCsv(e.target.value)}
              />
            </label>

            <label className="form-group">
              Risk tolerance (0 conservative → 100 aggressive)
              <input
                type="number"
                min={0}
                max={100}
                value={userRiskTolerance}
                onChange={(e) => setUserRiskTolerance(Number(e.target.value))}
              />
            </label>

            <label className="form-group">
              top_k
              <input
                type="number"
                min={1}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
              />
            </label>

            <label className="form-group">
              max weight
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={maxWeight}
                onChange={(e) => setMaxWeight(Number(e.target.value))}
              />
            </label>

            <label className="form-group">
              min weight
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={minWeight}
                onChange={(e) => setMinWeight(Number(e.target.value))}
              />
            </label>

            <label
              className="form-group"
              style={{ gridTemplateColumns: "18px 1fr", alignItems: "center", gap: 8 }}
            >
              <input
                type="checkbox"
                checked={allowCash}
                onChange={(e) => setAllowCash(e.target.checked)}
                style={{ width: 16, minHeight: 16, height: 16, margin: 0 }}
              />
              <span>allow_cash</span>
            </label>

            <label
              className="form-group"
              style={{ gridTemplateColumns: "18px 1fr", alignItems: "center", gap: 8 }}
            >
              <input
                type="checkbox"
                checked={includeExplanation}
                onChange={(e) => setIncludeExplanation(e.target.checked)}
                style={{ width: 16, minHeight: 16, height: 16, margin: 0 }}
              />
              <span>Include explanation</span>
            </label>

            <label className="form-group">
              Explanation mode
              <select
                value={explanationMode}
                onChange={(e) => setExplanationMode(e.target.value as "fallback" | "llm")}
              >
                <option value="fallback">fallback</option>
                <option value="llm">llm</option>
              </select>
            </label>

            <button className="primary-btn" onClick={() => mut.mutate(req)}>
              Recommend portfolio
            </button>
          </div>
        </Card>

        <Card title="Request JSON (debug)">
          <div className="json-panel">
            <JsonPanel data={req} />
          </div>
        </Card>
      </div>

      <div className="content-stack">
        {mut.isPending ? <Loading label="Running portfolio optimization…" /> : null}
        {mut.error ? <ErrorBanner error={mut.error} /> : null}

        {mut.data ? (
          <>
            <Card title="Summary">
              <div className="kpi-grid">
                {kpi("Engine", engine)}
                {kpi("Horizon", `${horizonDays} days`)}
                {kpi("# scenarios", String(nScenarios))}
                {kpi("Assets", String(req.symbols.length))}
              </div>

              <div style={{ height: 12 }} />

              <div className="kpi-grid">
                {kpi(
                  "portfolio_expected_return",
                  Number.isFinite(portfolioExpectedReturn) ? pct(portfolioExpectedReturn) : "—"
                )}
                {kpi("portfolio_cvar", Number.isFinite(portfolioCvar) ? num(portfolioCvar) : "—")}
                {kpi(
                  "portfolio_max_drawdown_est",
                  Number.isFinite(portfolioMaxDrawdown) ? num(portfolioMaxDrawdown) : "—"
                )}
                {kpi("allow_cash", allowCash ? "true" : "false")}
              </div>
            </Card>

            <WeightsBars weights={weights} />

            <Card title="Risk JSON">
              <div className="json-panel">
                <JsonPanel data={mut.data.risks} />
              </div>
            </Card>

            <Card title="Portfolio JSON">
              <div className="json-panel">
                <JsonPanel data={mut.data.portfolio} />
              </div>
            </Card>

            <Card title="Explanation">
              <div className="json-panel">
                <JsonPanel data={mut.data.explanation} />
              </div>
            </Card>
          </>
        ) : (
          <Card title="What you’ll see here">
            <div style={{ color: "#444", lineHeight: 1.5 }}>
              Run the portfolio optimizer to see weights, risk JSON, portfolio output, and explanation.
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}