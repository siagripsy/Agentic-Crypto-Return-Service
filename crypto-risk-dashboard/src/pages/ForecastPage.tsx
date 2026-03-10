import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Card from "../components/Card";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";
import JsonPanel from "../components/JsonPanel";
import SummaryCharts from "../components/charts/SummaryCharts";
import { api } from "../api/client";
import type {
  EngineType,
  HorizonRequest,
  HorizonResponse,
  MultiHorizonRequest,
  MultiHorizonResponse,
  ReturnFormat,
  RiskLevel
} from "../api/types";
import { num } from "../utils/format";

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

const PATH_ENGINES: EngineType[] = ["walkforward_ml", "regime_similarity"];

export default function ForecastPage() {
  const [forecastScope, setForecastScope] = useState<"single" | "multi">("single");

  const [symbol, setSymbol] = useState("BTC");
  const [symbolsCsv, setSymbolsCsv] = useState("BTC, ETH, SOL");

  const [startDate, setStartDate] = useState("2025-12-01");
  const [endDate, setEndDate] = useState("2025-12-11");
  const [horizonDays, setHorizonDays] = useState(10);
  const [forecastMode, setForecastMode] = useState<"end_date" | "horizon_days">("horizon_days");

  const [engine, setEngine] = useState<EngineType>("ensemble");
  const [nScenarios, setNScenarios] = useState(1000);
  const [alpha, setAlpha] = useState(0.05);
  const [riskLevel, setRiskLevel] = useState<RiskLevel | "">("");

  const [returnFormat, setReturnFormat] = useState<ReturnFormat>("both");
  const [includeExplanation, setIncludeExplanation] = useState(true);
  const [explanationMode, setExplanationMode] = useState<"fallback" | "llm">("fallback");

  const isPathEngine = PATH_ENGINES.includes(engine);

  useEffect(() => {
    if (isPathEngine && forecastMode !== "horizon_days") {
      setForecastMode("horizon_days");
    }
  }, [engine, forecastMode, isPathEngine]);

  const singleReq: HorizonRequest = useMemo(
    () => ({
      symbol: symbol.trim().toUpperCase(),
      start_date: startDate,
      end_date: !isPathEngine && forecastMode === "end_date" ? (endDate || null) : null,
      horizon_days: isPathEngine || forecastMode === "horizon_days" ? horizonDays : null,
      engine,
      n_scenarios: nScenarios,
      alpha,
      risk_level: riskLevel || null,
      alphas: null,
      seed: 42,
      return_format: returnFormat,
      timeout_seconds: 30,
      include_explanation: includeExplanation,
      explanation_mode: explanationMode
    }),
    [
      symbol,
      startDate,
      endDate,
      horizonDays,
      forecastMode,
      isPathEngine,
      engine,
      nScenarios,
      alpha,
      riskLevel,
      returnFormat,
      includeExplanation,
      explanationMode
    ]
  );

  const multiReq: MultiHorizonRequest = useMemo(
    () => ({
      symbols: parseSymbols(symbolsCsv),
      start_date: startDate,
      end_date: !isPathEngine && forecastMode === "end_date" ? (endDate || null) : null,
      horizon_days: isPathEngine || forecastMode === "horizon_days" ? horizonDays : null,
      engine,
      n_scenarios: nScenarios,
      alpha,
      risk_level: riskLevel || null,
      alphas: null,
      seed: 42,
      return_format: returnFormat,
      timeout_seconds: 30,
      include_explanation: includeExplanation,
      explanation_mode: explanationMode
    }),
    [
      symbolsCsv,
      startDate,
      endDate,
      horizonDays,
      forecastMode,
      isPathEngine,
      engine,
      nScenarios,
      alpha,
      riskLevel,
      returnFormat,
      includeExplanation,
      explanationMode
    ]
  );

  const singleMut = useMutation<HorizonResponse, Error, HorizonRequest>({
    mutationFn: (r) => api.forecastHorizon(r)
  });

  const multiMut = useMutation<MultiHorizonResponse, Error, MultiHorizonRequest>({
    mutationFn: (r) => api.forecastHorizonMulti(r)
  });

  const activeLoading = forecastScope === "single" ? singleMut.isPending : multiMut.isPending;
  const activeError = forecastScope === "single" ? singleMut.error : multiMut.error;

  const singleData = singleMut.data ?? null;
  const multiData = multiMut.data ?? null;

  const singleMetricBlock =
    returnFormat === "log"
      ? singleData?.metrics?.log ?? null
      : returnFormat === "simple"
        ? singleData?.metrics?.simple ?? null
        : singleData?.metrics?.simple ?? singleData?.metrics?.log ?? null;

  return (
    <div className="dashboard-grid">
      <div className="sidebar-stack">
        <Card title="Forecast controls">
          <div className="form-grid">
            <label className="form-group">
              Forecast scope
              <select
                value={forecastScope}
                onChange={(e) => setForecastScope(e.target.value as "single" | "multi")}
              >
                <option value="single">Single forecast</option>
                <option value="multi">Multi forecast</option>
              </select>
            </label>

            {forecastScope === "single" ? (
              <label className="form-group">
                Symbol
                <input value={symbol} onChange={(e) => setSymbol(e.target.value)} />
              </label>
            ) : (
              <label className="form-group">
                Symbols (comma-separated)
                <input value={symbolsCsv} onChange={(e) => setSymbolsCsv(e.target.value)} />
              </label>
            )}

            <label className="form-group">
              Start date
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </label>

            <label className="form-group">
              Forecast mode
              <select
                value={forecastMode}
                disabled={isPathEngine}
                onChange={(e) => setForecastMode(e.target.value as "end_date" | "horizon_days")}
              >
                <option value="horizon_days">Use horizon days</option>
                <option value="end_date">Use end date</option>
              </select>
            </label>

            {isPathEngine ? (
              <div className="helper-text">
                This engine requires horizon days. End date mode is disabled.
              </div>
            ) : null}

            {forecastMode === "end_date" && !isPathEngine ? (
              <label className="form-group">
                End date
                <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </label>
            ) : (
              <label className="form-group">
                Horizon days
                <input
                  type="number"
                  value={horizonDays}
                  min={1}
                  max={252}
                  onChange={(e) => setHorizonDays(Number(e.target.value))}
                />
              </label>
            )}

            <label className="form-group">
              Engine
              <select value={engine} onChange={(e) => setEngine(e.target.value as EngineType)}>
                <option value="fast_regime_fixed">fast_regime_fixed</option>
                <option value="walkforward_ml">walkforward_ml</option>
                <option value="regime_similarity">regime_similarity</option>
                <option value="ensemble">ensemble</option>
              </select>
            </label>

            <label className="form-group">
              # scenarios
              <input
                type="number"
                value={nScenarios}
                min={100}
                max={20000}
                onChange={(e) => setNScenarios(Number(e.target.value))}
              />
            </label>

            <label className="form-group">
              Alpha (tail probability)
              <input
                type="number"
                value={alpha}
                step={0.01}
                min={0.001}
                max={0.49}
                onChange={(e) => setAlpha(Number(e.target.value))}
              />
            </label>

            <label className="form-group">
              Risk level (optional)
              <select value={riskLevel} onChange={(e) => setRiskLevel(e.target.value as RiskLevel | "")}>
                <option value="">(none)</option>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </label>

            <label className="form-group">
              Return format
              <select
                value={returnFormat}
                onChange={(e) => setReturnFormat(e.target.value as ReturnFormat)}
              >
                <option value="both">both</option>
                <option value="log">log</option>
                <option value="simple">simple</option>
              </select>
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

            <button
              className="primary-btn"
              onClick={() => {
                if (forecastScope === "single") {
                  singleMut.mutate(singleReq);
                } else {
                  multiMut.mutate(multiReq);
                }
              }}
            >
              {forecastScope === "single" ? "Run forecast" : "Run multi forecast"}
            </button>
          </div>
        </Card>

        <Card title="Request JSON (debug)">
          <div className="json-panel">
            <JsonPanel data={forecastScope === "single" ? singleReq : multiReq} />
          </div>
        </Card>
      </div>

      <div className="content-stack">
        {activeLoading ? (
          <Loading label={forecastScope === "single" ? "Running forecast…" : "Running multi forecast…"} />
        ) : null}

        {activeError ? <ErrorBanner error={activeError} /> : null}

        {forecastScope === "single" ? (
          singleData ? (
            <>
              <Card title="At-a-glance">
                <div className="kpi-grid">
                  {kpi("Engine", String(singleData.engine))}
                  {kpi("Horizon", `${singleData.horizon_days} days`)}
                  {kpi("# scenarios", String(singleData.n_scenarios))}
                  {kpi("Alpha", String(singleData.alpha))}
                </div>

                <div style={{ height: 12 }} />

                {singleData.summary ? (
                  <div className="kpi-grid">
                    {kpi("Mean (terminal)", num(singleData.summary.mean ?? NaN))}
                    {kpi("Median (terminal)", num(singleData.summary.median ?? NaN))}
                    {kpi("p05 (terminal)", num(singleData.summary.p05 ?? NaN))}
                    {kpi("p95 (terminal)", num(singleData.summary.p95 ?? NaN))}
                  </div>
                ) : (
                  <div className="helper-text">
                    Using metric-based charts from the returned summary statistics below.
                  </div>
                )}
              </Card>

              <SummaryCharts
                block={singleMetricBlock}
                label={returnFormat === "both" ? "Displayed metric block" : returnFormat}
              />

              {returnFormat === "both" ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                  <Card title="Log metrics JSON">
                    <div className="json-panel">
                      <JsonPanel data={singleData.metrics?.log ?? null} />
                    </div>
                  </Card>
                  <Card title="Simple metrics JSON">
                    <div className="json-panel">
                      <JsonPanel data={singleData.metrics?.simple ?? null} />
                    </div>
                  </Card>
                </div>
              ) : (
                <Card title="Metrics JSON">
                  <div className="json-panel">
                    <JsonPanel data={singleData.metrics} />
                  </div>
                </Card>
              )}

              <Card title="Explanation">
                <div className="json-panel">
                  <JsonPanel data={singleData.explanation} />
                </div>
              </Card>
            </>
          ) : (
            <Card title="What you’ll see here">
              <div style={{ color: "#444", lineHeight: 1.5 }}>
                Run a single-asset forecast to see summary charts, raw metrics, and explanation output.
              </div>
            </Card>
          )
        ) : multiData ? (
          <>
            <Card title="Multi forecast overview">
              <div className="kpi-grid">
                {kpi("Assets", String(multiData.results.length))}
                {kpi("Engine", String(multiData.results[0]?.engine ?? "—"))}
                {kpi("Horizon", `${multiData.results[0]?.horizon_days ?? "—"} days`)}
                {kpi("# scenarios", String(multiData.results[0]?.n_scenarios ?? "—"))}
              </div>
            </Card>

            {multiData.results.map((item) => {
              const block =
                returnFormat === "log"
                  ? item.metrics?.log ?? null
                  : returnFormat === "simple"
                    ? item.metrics?.simple ?? null
                    : item.metrics?.simple ?? item.metrics?.log ?? null;

              return (
                <div key={item.symbol} className="content-stack">
                  <Card title={`${item.symbol} — at a glance`}>
                    <div className="kpi-grid">
                      {kpi("Engine", String(item.engine))}
                      {kpi("Horizon", `${item.horizon_days} days`)}
                      {kpi("# scenarios", String(item.n_scenarios))}
                      {kpi("Alpha", String(item.alpha))}
                    </div>

                    <div style={{ height: 12 }} />

                    {item.summary ? (
                      <div className="kpi-grid">
                        {kpi("Mean (terminal)", num(item.summary.mean ?? NaN))}
                        {kpi("Median (terminal)", num(item.summary.median ?? NaN))}
                        {kpi("p05 (terminal)", num(item.summary.p05 ?? NaN))}
                        {kpi("p95 (terminal)", num(item.summary.p95 ?? NaN))}
                      </div>
                    ) : (
                      <div className="helper-text">
                        Using metric-based charts from returned summary statistics.
                      </div>
                    )}
                  </Card>

                  <SummaryCharts
                    block={block}
                    label={`${item.symbol} ${returnFormat === "both" ? "displayed metric block" : returnFormat}`}
                  />

                  {returnFormat === "both" ? (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                      <Card title={`${item.symbol} — log metrics JSON`}>
                        <div className="json-panel">
                          <JsonPanel data={item.metrics?.log ?? null} />
                        </div>
                      </Card>
                      <Card title={`${item.symbol} — simple metrics JSON`}>
                        <div className="json-panel">
                          <JsonPanel data={item.metrics?.simple ?? null} />
                        </div>
                      </Card>
                    </div>
                  ) : (
                    <Card title={`${item.symbol} — metrics JSON`}>
                      <div className="json-panel">
                        <JsonPanel data={item.metrics} />
                      </div>
                    </Card>
                  )}

                  <Card title={`${item.symbol} — explanation`}>
                    <div className="json-panel">
                      <JsonPanel data={item.explanation} />
                    </div>
                  </Card>
                </div>
              );
            })}
          </>
        ) : (
          <Card title="What you’ll see here">
            <div style={{ color: "#444", lineHeight: 1.5 }}>
              Run a multi-asset forecast to see one result block per symbol, including charts, raw
              metrics, and explanation.
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}