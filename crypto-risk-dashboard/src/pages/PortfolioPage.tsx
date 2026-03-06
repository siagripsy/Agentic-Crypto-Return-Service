import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Card from "../components/Card";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";
import JsonPanel from "../components/JsonPanel";
import WeightsBar from "../components/charts/WeightsBar";
import { api } from "../api/client";
import type { PortfolioRequest, PortfolioResponse, PortfolioEngine } from "../api/types";
import { num, pct } from "../utils/format";

function parseSymbols(input: string): string[] {
  return input
    .split(",")
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export default function PortfolioPage() {
  const [symbolsCsv, setSymbolsCsv] = useState("BTC,ETH,SOL,XRP,BNB");
  const [startDate, setStartDate] = useState("2025-12-01");
  const [horizonDays, setHorizonDays] = useState(21);

  const [engine, setEngine] = useState<PortfolioEngine>("ensemble");
  const [nScenarios, setNScenarios] = useState(3000);
  const [topK, setTopK] = useState(5);
  const [maxWeight, setMaxWeight] = useState(0.5);
  const [minWeight, setMinWeight] = useState(0.0);
  const [allowCash, setAllowCash] = useState(true);

  const [riskTol, setRiskTol] = useState(50);
  const [confLevels, setConfLevels] = useState("0.95");

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

      confidence_levels: confLevels
        .split(",")
        .map((x) => Number(x.trim()))
        .filter((x) => Number.isFinite(x)),

      user_risk_tolerance: riskTol,
      top_k: topK,
      max_weight: maxWeight,
      min_weight: minWeight,
      allow_cash: allowCash,

      timeout_seconds: 30,

      include_explanation: includeExplanation,
      explanation_mode: explanationMode
    }),
    [symbolsCsv, startDate, horizonDays, engine, nScenarios, topK, maxWeight, minWeight, allowCash, riskTol, confLevels, includeExplanation, explanationMode]
  );

  const mut = useMutation<PortfolioResponse, Error, PortfolioRequest>({
    mutationFn: (r) => api.portfolioRecommend(r)
  });

  // Best-effort: common patterns for weights in portfolio output
  const weights: Record<string, number> | null =
    (mut.data?.portfolio as any)?.weights ??
    (mut.data?.portfolio as any)?.allocation ??
    (mut.data?.portfolio as any)?.w ??
    null;

  // Best-effort: portfolio KPIs if present
  const portfolioKpis = mut.data?.portfolio ?? null;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 16 }}>
      {/* Controls */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <Card title="Portfolio controls">
          <div style={{ display: "grid", gap: 10 }}>
            <label>
              Symbols (comma-separated)
              <input value={symbolsCsv} onChange={(e) => setSymbolsCsv(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label>
              Start date
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label>
              Horizon days
              <input type="number" value={horizonDays} min={1} max={252} onChange={(e) => setHorizonDays(Number(e.target.value))} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label>
              Engine
              <select value={engine} onChange={(e) => setEngine(e.target.value as PortfolioEngine)} style={{ width: "100%", padding: 8, marginTop: 4 }}>
                <option value="walkforward_ml">walkforward_ml</option>
                <option value="regime_similarity">regime_similarity</option>
                <option value="ensemble">ensemble</option>
              </select>
            </label>

            <label>
              # scenarios
              <input type="number" value={nScenarios} min={100} max={20000} onChange={(e) => setNScenarios(Number(e.target.value))} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label>
              Confidence levels (comma-separated)
              <input value={confLevels} onChange={(e) => setConfLevels(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label>
              Risk tolerance (0 conservative → 100 aggressive)
              <input type="number" value={riskTol} min={0} max={100} onChange={(e) => setRiskTol(Number(e.target.value))} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label>
              top_k
              <input type="number" value={topK} min={1} max={20} onChange={(e) => setTopK(Number(e.target.value))} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label>
              max_weight
              <input type="number" value={maxWeight} step={0.05} min={0.05} max={1} onChange={(e) => setMaxWeight(Number(e.target.value))} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label>
              min_weight
              <input type="number" value={minWeight} step={0.01} min={0} max={1} onChange={(e) => setMinWeight(Number(e.target.value))} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={allowCash} onChange={(e) => setAllowCash(e.target.checked)} />
              allow_cash
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={includeExplanation} onChange={(e) => setIncludeExplanation(e.target.checked)} />
              Include explanation
            </label>

            <label>
              Explanation mode
              <select value={explanationMode} onChange={(e) => setExplanationMode(e.target.value as any)} style={{ width: "100%", padding: 8, marginTop: 4 }}>
                <option value="fallback">fallback</option>
                <option value="llm">llm</option>
              </select>
            </label>

            <button
              onClick={() => mut.mutate(req)}
              style={{
                padding: "10px 12px",
                borderRadius: 12,
                border: "1px solid #111",
                background: "#111",
                color: "white",
                fontWeight: 800,
                cursor: "pointer"
              }}
            >
              Recommend portfolio
            </button>
          </div>
        </Card>

        <Card title="Request JSON (debug)">
          <JsonPanel data={req} />
        </Card>
      </div>

      {/* Results */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {mut.isPending ? <Loading label="Running portfolio optimization…" /> : null}
        {mut.error ? <ErrorBanner error={mut.error} /> : null}

        {mut.data ? (
          <>
            <Card title="Summary">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
                <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                  <div style={{ color: "#666", fontSize: 12 }}>Engine</div>
                  <div style={{ fontWeight: 800 }}>{engine}</div>
                </div>
                <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                  <div style={{ color: "#666", fontSize: 12 }}>Horizon</div>
                  <div style={{ fontWeight: 800 }}>{horizonDays} days</div>
                </div>
                <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                  <div style={{ color: "#666", fontSize: 12 }}># scenarios</div>
                  <div style={{ fontWeight: 800 }}>{nScenarios}</div>
                </div>
                <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                  <div style={{ color: "#666", fontSize: 12 }}>Assets</div>
                  <div style={{ fontWeight: 800 }}>{req.symbols.length}</div>
                </div>
              </div>

              <div style={{ marginTop: 10, color: "#666", fontSize: 12 }}>
                KPI fields depend on your portfolio output schema; weights + risks are always shown.
              </div>

              {/* Best-effort: show common fields if present */}
              <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
                <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                  <div style={{ color: "#666", fontSize: 12 }}>portfolio_expected_return</div>
                  <div style={{ fontWeight: 800 }}>{portfolioKpis?.portfolio_expected_return ? pct(Number(portfolioKpis.portfolio_expected_return)) : "—"}</div>
                </div>
                <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                  <div style={{ color: "#666", fontSize: 12 }}>portfolio_cvar</div>
                  <div style={{ fontWeight: 800 }}>{portfolioKpis?.portfolio_cvar ? num(Number(portfolioKpis.portfolio_cvar)) : "—"}</div>
                </div>
                <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                  <div style={{ color: "#666", fontSize: 12 }}>portfolio_max_drawdown_est</div>
                  <div style={{ fontWeight: 800 }}>{portfolioKpis?.portfolio_max_drawdown_est ? num(Number(portfolioKpis.portfolio_max_drawdown_est)) : "—"}</div>
                </div>
              </div>
            </Card>

            <WeightsBar weights={weights ?? undefined} />

            <Card title="Risks JSON">
              <JsonPanel data={mut.data.risks} />
            </Card>

            <Card title="Portfolio JSON">
              <JsonPanel data={mut.data.portfolio} />
            </Card>

            <Card title="Explanation">
              <JsonPanel data={mut.data.explanation} />
            </Card>
          </>
        ) : (
          <Card title="What you’ll see here">
            <div style={{ color: "#444", lineHeight: 1.4 }}>
              This page calls <code>/portfolio/recommend</code> and renders:
              <ul>
                <li>Recommended weights chart</li>
                <li>Risk object + portfolio object (full JSON)</li>
                <li>Optional explanation payload</li>
              </ul>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}