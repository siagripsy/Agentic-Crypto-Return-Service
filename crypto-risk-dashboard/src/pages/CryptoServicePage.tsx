import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  AssetOption,
  CryptoReturnServiceRequest,
  CryptoReturnServiceResponse,
  ExplanationMode,
  ExplanationSection,
  PortfolioDetail,
  RegimeMatchingBlock,
  RiskReport,
  ScenarioEngineBlock
} from "../api/types";
import AnalysisLoadingOverlay from "../components/AnalysisLoadingOverlay";
import AssetAllocationFormRows, { type AssetRowValue } from "../components/AssetAllocationFormRows";
import Card from "../components/Card";
import ErrorBanner from "../components/ErrorBanner";
import RegimeBubbleChart from "../components/RegimeBubbleChart";
import RiskReturnBubbleChart from "../components/RiskReturnBubbleChart";
import ScenarioBoxPlot from "../components/ScenarioBoxPlot";
import ScenarioFanChart from "../components/ScenarioFanChart";
import SummaryKpis from "../components/SummaryKpis";
import { buildTerminalReturnBoxStats } from "../utils/cryptoService";
import { num, pct } from "../utils/format";

type TabKey = "input" | "summary" | "regime" | "scenarios" | "risk";

const TAB_META: { key: TabKey; label: string; index: string }[] = [
  { key: "input", label: "Input", index: "01" },
  { key: "summary", label: "Summary", index: "02" },
  { key: "regime", label: "Regime Matching", index: "03" },
  { key: "scenarios", label: "Scenarios", index: "04" },
  { key: "risk", label: "Risk & Portfolio", index: "05" }
];

function buildRequest(
  rows: AssetRowValue[],
  capital: string,
  horizonDays: string,
  nScenarios: string,
  riskTolerancePct: string,
  explanationMode: ExplanationMode
): CryptoReturnServiceRequest {
  const assets: Record<string, number> = {};
  rows.forEach((row) => {
    const pctValue = Number(row.percentage);
    if (row.ticker && Number.isFinite(pctValue) && row.percentage !== "") {
      assets[row.ticker] = pctValue / 100;
    }
  });

  return {
    capital: Number(capital),
    assets,
    horizon_days: Number(horizonDays),
    n_scenarios: Number(nScenarios),
    risk_tolerance: Number(riskTolerancePct) / 100,
    include_explanation: true,
    explanation_mode: explanationMode
  };
}

function validateForm(
  rows: AssetRowValue[],
  capital: string,
  horizonDays: string,
  nScenarios: string,
  riskTolerancePct: string,
  options: AssetOption[]
) {
  const errors: Record<string, string[]> = {
    capital: [],
    assets: [],
    horizon: [],
    scenarios: [],
    risk: []
  };

  const capitalValue = Number(capital);
  if (capital.trim() === "" || !Number.isFinite(capitalValue) || capitalValue <= 0) {
    errors.capital.push("Capital must be a positive dollar amount.");
  }

  const horizonValue = Number(horizonDays);
  if (horizonDays.trim() === "" || !Number.isInteger(horizonValue) || horizonValue <= 1) {
    errors.horizon.push("Horizon days must be an integer greater than 1.");
  }

  const scenariosValue = Number(nScenarios);
  if (nScenarios.trim() === "" || !Number.isInteger(scenariosValue) || scenariosValue <= 5) {
    errors.scenarios.push("Number of scenarios must be an integer greater than 5.");
  }

  const riskValue = Number(riskTolerancePct);
  if (riskTolerancePct.trim() === "" || !Number.isFinite(riskValue) || riskValue < 0 || riskValue > 100) {
    errors.risk.push("Risk tolerance must be between 0 and 100 percent.");
  }

  const selected = rows.map((row) => row.ticker).filter(Boolean);
  const duplicateCount = selected.length - new Set(selected).size;
  if (!selected.length) {
    errors.assets.push("Select at least one asset.");
  }
  if (duplicateCount > 0) {
    errors.assets.push("Duplicate asset selections are not allowed.");
  }
  if (selected.length > options.length) {
    errors.assets.push("You selected more assets than are available.");
  }

  const filledRows = rows.filter((row) => row.ticker || row.percentage !== "");
  if (!filledRows.length) {
    errors.assets.push("Add at least one asset and weight.");
  }

  const total = rows.reduce((sum, row) => sum + (Number(row.percentage) || 0), 0);
  if (Math.abs(total - 100) > 1e-6) {
    errors.assets.push(`Asset percentages must sum to exactly 100%. Current total: ${total.toFixed(2)}%.`);
  }

  rows.forEach((row) => {
    if (row.ticker || row.percentage !== "") {
      if (!row.ticker) {
        errors.assets.push("Each asset row needs a selected asset.");
      }
      const value = Number(row.percentage);
      if (!Number.isFinite(value) || value < 0) {
        errors.assets.push("Each asset row needs a valid percentage.");
      }
    }
  });

  return errors;
}

function emptyState(message: string) {
  return (
    <Card title="Run an analysis first" className="empty-analysis-card">
      <div className="hero-copy">{message}</div>
    </Card>
  );
}

function sectionCard(title: string, section?: ExplanationSection) {
  if (!section) return null;
  return (
    <Card title={title} className="analysis-card">
      <div className="analysis-lead">{section.headline}</div>
      <ul className="analysis-bullets">
        {section.bullets.map((bullet, index) => (
          <li key={`${title}-${index}`}>{bullet}</li>
        ))}
      </ul>
    </Card>
  );
}

function regimeMetricItems(asset: string, block: RegimeMatchingBlock) {
  const summary = block.summary ?? {};
  const profits = summary.profit_analysis ?? {};
  const losses = summary.loss_analysis ?? {};
  const drawdowns = summary.drawdown_analysis ?? {};

  return [
    { label: `${asset} best profit rate`, value: pct(Number(summary.prob_profit ?? Number.NaN)) },
    { label: "Avg profitable gain", value: pct(Number(profits.mean_profit ?? Number.NaN)) },
    { label: "Avg losing move", value: pct(Number(losses.mean_loss ?? Number.NaN)) },
    { label: "Worst loss", value: pct(Number(losses.worst_loss ?? Number.NaN)) },
    { label: "Avg drawdown", value: pct(Number(drawdowns.mean_max_drawdown ?? Number.NaN)) }
  ];
}

function scenarioMetricItems(asset: string, block: ScenarioEngineBlock) {
  const summary = block.summary;
  const startPrice = Number(summary.start_price ?? Number.NaN);
  const meanReturn = startPrice ? Number(summary.terminal_mean) / startPrice - 1 : Number.NaN;
  const medianReturn = startPrice ? Number(summary.terminal_median) / startPrice - 1 : Number.NaN;
  const downside = startPrice ? Number(summary.terminal_p05) / startPrice - 1 : Number.NaN;
  const upside = startPrice ? Number(summary.terminal_p95) / startPrice - 1 : Number.NaN;

  return [
    { label: `${asset} median return`, value: pct(medianReturn) },
    { label: "Expected return", value: pct(meanReturn) },
    { label: "Downside p05", value: pct(downside) },
    { label: "Upside p95", value: pct(upside) },
    { label: "Price span", value: `${num(summary.terminal_p05, 2)} to ${num(summary.terminal_p95, 2)}` }
  ];
}

function regimeNarrative(asset: string, block: RegimeMatchingBlock) {
  const summary = block.summary ?? {};
  const profits = summary.profit_analysis ?? {};
  const losses = summary.loss_analysis ?? {};
  const drawdowns = summary.drawdown_analysis ?? {};
  const topMatch = block.matches?.[0];

  return (
    <Card title={`${asset} interpretation`} className="analysis-card">
      <ul className="analysis-bullets">
        <li>{asset} shows a historical profit rate of {pct(Number(summary.prob_profit ?? Number.NaN))} across its closest analog windows.</li>
        <li>Average profitable analogs returned {pct(Number(profits.mean_profit ?? Number.NaN))}, while losing analogs averaged {pct(Number(losses.mean_loss ?? Number.NaN))}.</li>
        <li>The average maximum drawdown during matched windows was {pct(Number(drawdowns.mean_max_drawdown ?? Number.NaN))}, which shows how much pain may arrive before recovery.</li>
        <li>The worst matched loss was {pct(Number(losses.worst_loss ?? Number.NaN))}, which is the tail case to compare against your own downside tolerance.</li>
        {topMatch ? <li>The closest historical analog ended on {topMatch.forward_end_date} with {pct(topMatch.profit_pct)} forward return and {pct(topMatch.max_drawdown_pct)} max drawdown.</li> : null}
      </ul>
    </Card>
  );
}

function scenarioNarrative(asset: string, block: ScenarioEngineBlock) {
  const summary = block.summary;
  const startPrice = Number(summary.start_price ?? Number.NaN);
  const downside = startPrice ? Number(summary.terminal_p05) / startPrice - 1 : Number.NaN;
  const median = startPrice ? Number(summary.terminal_p50) / startPrice - 1 : Number.NaN;
  const upside = startPrice ? Number(summary.terminal_p95) / startPrice - 1 : Number.NaN;

  return (
    <Card title={`${asset} interpretation`} className="analysis-card">
      <ul className="analysis-bullets">
        <li>The median scenario for {asset} implies a terminal return of {pct(median)} over the selected horizon.</li>
        <li>The lower tail reaches about {pct(downside)} at p05, which marks the adverse but still plausible downside band.</li>
        <li>The upper tail reaches about {pct(upside)} at p95, which shows how far the stronger scenarios extend.</li>
        <li>A wide gap between p05 and p95 means {asset} has more uncertainty across the simulated paths, while a tighter gap means more concentrated outcomes.</li>
        <li>The fan chart is best read as a cone of dispersion: the center path is typical, but the outer band is where uncertainty becomes material.</li>
      </ul>
    </Card>
  );
}

function riskNarrative(details: PortfolioDetail[], topWeight?: PortfolioDetail | null) {
  if (!details.length) return null;

  return (
    <Card title="How to read the risk map" className="analysis-card">
      <ul className="analysis-bullets">
        <li>Each bubble is one asset: higher means higher expected return, farther right means larger downside tail loss magnitude, and larger size means heavier suggested portfolio weight.</li>
        <li>Assets closer to the upper-left area are generally more attractive because they combine lower downside with higher expected return.</li>
        <li>If an asset sits high but far right, it may offer upside at the cost of more severe tail loss risk.</li>
        {topWeight ? <li>{topWeight.symbol} currently receives the heaviest suggested weight at {pct(topWeight.weight)}, so it contributes most to overall portfolio behavior.</li> : null}
        <li>The suggested weights chart shows the optimizer output after balancing expected return against CVaR and drawdown constraints.</li>
      </ul>
    </Card>
  );
}

export default function CryptoServicePage() {
  const [capital, setCapital] = useState("");
  const [rows, setRows] = useState<AssetRowValue[]>([{ ticker: "", percentage: "" }]);
  const [horizonDays, setHorizonDays] = useState("");
  const [nScenarios, setNScenarios] = useState("");
  const [riskTolerancePct, setRiskTolerancePct] = useState("");
  const [explanationMode, setExplanationMode] = useState<ExplanationMode>("llm");
  const [activeTab, setActiveTab] = useState<TabKey>("input");

  const assetsQuery = useQuery({
    queryKey: ["asset-options"],
    queryFn: api.getAssetOptions
  });

  const options = assetsQuery.data?.items ?? [];
  const validation = useMemo(
    () => validateForm(rows, capital, horizonDays, nScenarios, riskTolerancePct, options),
    [rows, capital, horizonDays, nScenarios, riskTolerancePct, options]
  );
  const isValid = Object.values(validation).every((group) => group.length === 0);
  const requestPreview = useMemo(
    () => buildRequest(rows, capital, horizonDays, nScenarios, riskTolerancePct, explanationMode),
    [rows, capital, horizonDays, nScenarios, riskTolerancePct, explanationMode]
  );

  const mutation = useMutation<CryptoReturnServiceResponse, Error, CryptoReturnServiceRequest>({
    mutationFn: (req) => api.cryptoReturnService(req)
  });

  useEffect(() => {
    if (mutation.data) {
      setActiveTab("summary");
    }
  }, [mutation.data]);

  const selectedTab = TAB_META.find((tab) => tab.key === activeTab) ?? TAB_META[0];
  const response = mutation.data;
  const explanation = response?.explanation;
  const selectedAssetLabels = rows.map((row) => row.ticker).filter(Boolean);
  const weightSummary = rows
    .filter((row) => row.ticker && row.percentage !== "")
    .map((row) => `${row.ticker} ${row.percentage}%`)
    .join(" • ");

  const regimeEntries = Object.entries(response?.regime_matching ?? {});
  const scenarioEntries = Object.entries(response?.scenario_engine ?? {});
  const portfolioDetails = response?.portfolio.details ?? [];

  const bestRegime = useMemo(() => {
    return regimeEntries.reduce<{ asset: string; prob: number } | null>((best, [asset, block]) => {
      const prob = Number(block.summary?.prob_profit);
      if (!Number.isFinite(prob)) return best;
      if (!best || prob > best.prob) return { asset, prob };
      return best;
    }, null);
  }, [regimeEntries]);

  const topScenario = useMemo(() => {
    return scenarioEntries.reduce<{ asset: string; median: number } | null>((best, [asset, block]) => {
      const median = Number(block.summary?.terminal_p50);
      if (!Number.isFinite(median)) return best;
      if (!best || median > best.median) return { asset, median };
      return best;
    }, null);
  }, [scenarioEntries]);

  const topWeight = useMemo(() => {
    return portfolioDetails.reduce<PortfolioDetail | null>((best, detail) => {
      if (!best || detail.weight > best.weight) return detail;
      return best;
    }, null);
  }, [portfolioDetails]);

  const inputTab = (
    <div className="content-stack">
      <div className="panel-hero">
        <div>
          <div className="panel-kicker">Request Builder</div>
          <h2>{selectedTab.label}</h2>
        </div>
        <div className="panel-badge">
          <span>{options.length || 0}</span>
          <small>available assets</small>
        </div>
      </div>

      {assetsQuery.isLoading ? <Card className="analysis-card">Loading assets...</Card> : null}
      {assetsQuery.error ? <ErrorBanner error={assetsQuery.error} /> : null}
      {mutation.error ? <ErrorBanner error={mutation.error} /> : null}

      <div className="insight-grid insight-grid-input">
        <Card title="Build request" className="input-form-card">
          <div className="form-grid">
            <label className="form-group">
              Capital
              <input type="number" min={0} value={capital} onChange={(e) => setCapital(e.target.value)} />
              {!!validation.capital.length && <div className="field-error">{validation.capital[0]}</div>}
            </label>

            <AssetAllocationFormRows
              rows={rows}
              options={options}
              errors={validation.assets}
              canAdd={rows.length < Math.max(options.length, 1)}
              onChange={(index, next) => setRows((current) => current.map((row, i) => (i === index ? next : row)))}
              onAdd={() => setRows((current) => [...current, { ticker: "", percentage: "" }])}
              onRemove={(index) => setRows((current) => (current.length <= 1 ? current : current.filter((_, i) => i !== index)))}
            />

            <label className="form-group">
              Horizon days
              <input type="number" min={2} value={horizonDays} onChange={(e) => setHorizonDays(e.target.value)} />
              {!!validation.horizon.length && <div className="field-error">{validation.horizon[0]}</div>}
            </label>

            <label className="form-group">
              Number of scenarios
              <input type="number" min={6} value={nScenarios} onChange={(e) => setNScenarios(e.target.value)} />
              {!!validation.scenarios.length && <div className="field-error">{validation.scenarios[0]}</div>}
            </label>

            <label className="form-group">
              Risk tolerance (%)
              <input
                type="number"
                min={0}
                max={100}
                value={riskTolerancePct}
                onChange={(e) => setRiskTolerancePct(e.target.value)}
              />
              {!!validation.risk.length && <div className="field-error">{validation.risk[0]}</div>}
            </label>

            <label className="form-group">
              Explanation mode
              <select value={explanationMode} onChange={(e) => setExplanationMode(e.target.value as ExplanationMode)}>
                <option value="llm">llm</option>
                <option value="fallback">fallback</option>
              </select>
            </label>

            <button
              className="primary-btn primary-btn-wide"
              type="button"
              disabled={!isValid || mutation.isPending || assetsQuery.isLoading}
              onClick={() => mutation.mutate(requestPreview)}
            >
              Analyze
            </button>
          </div>
        </Card>

        <div className="content-stack">
          <SummaryKpis
            items={[
              { label: "Assets", value: String(selectedAssetLabels.length) },
              { label: "Capital", value: capital ? `$${num(Number(capital), 0)}` : "-" },
              { label: "Horizon", value: horizonDays ? `${horizonDays}d` : "-" },
              { label: "Scenarios", value: nScenarios ? num(Number(nScenarios), 0) : "-" },
              { label: "Risk", value: riskTolerancePct ? `${riskTolerancePct}%` : "-" }
            ]}
          />
          <Card title="Current selection" className="analysis-card">
            <div className="compact-copy">{weightSummary || "No assets selected yet."}</div>
          </Card>
        </div>
      </div>
    </div>
  );

  const summaryTab = response ? (
    <div className="content-stack">
      <div className="panel-hero">
        <div>
          <div className="panel-kicker">Overview</div>
          <h2>{selectedTab.label}</h2>
        </div>
        <div className="panel-badge">
          <span>{portfolioDetails.length}</span>
          <small>assets in portfolio</small>
        </div>
      </div>

      <SummaryKpis
        items={[
          { label: "Best regime signal", value: bestRegime ? `${bestRegime.asset} ${pct(bestRegime.prob)}` : "-" },
          { label: "Top scenario median", value: topScenario ? `${topScenario.asset} ${num(topScenario.median, 2)}` : "-" },
          { label: "Portfolio return", value: pct(response.portfolio.portfolio_expected_return ?? Number.NaN) },
          { label: "Portfolio CVaR", value: pct(response.portfolio.portfolio_cvar ?? Number.NaN) },
          { label: "Top weight", value: topWeight ? `${topWeight.symbol} ${pct(topWeight.weight)}` : "-" }
        ]}
      />

      <div className="two-col-grid">
        <Card title="Overall interpretation" className="analysis-card">
          <div className="summary-banner">{explanation?.overall_summary ?? "Summary will appear here after the analysis completes."}</div>
        </Card>
        <Card title="Portfolio snapshot" className="analysis-card">
          <ul className="analysis-bullets">
            <li>The selected allocation is {weightSummary || "not yet available"}.</li>
            <li>The portfolio expected return is {pct(response.portfolio.portfolio_expected_return ?? Number.NaN)}.</li>
            <li>The portfolio CVaR is {pct(response.portfolio.portfolio_cvar ?? Number.NaN)}, which reflects the average of the worst tail outcomes.</li>
            <li>Estimated maximum drawdown is {pct(response.portfolio.portfolio_max_drawdown_est ?? Number.NaN)}.</li>
          </ul>
        </Card>
      </div>
    </div>
  ) : emptyState("Run the Input tab first to populate the summary view.");

  const regimeTab = response ? (
    <div className="content-stack">
      <div className="panel-hero">
        <div>
          <div className="panel-kicker">Historical analogs</div>
          <h2>{selectedTab.label}</h2>
        </div>
        <div className="panel-badge">
          <span>{regimeEntries.length}</span>
          <small>assets analyzed</small>
        </div>
      </div>

      {sectionCard("Regime interpretation", explanation?.sections?.regime_matching)}

      {regimeEntries.length ? (
        regimeEntries.map(([asset, block]) => (
          <div key={asset} className="content-stack asset-section">
            <SummaryKpis items={regimeMetricItems(asset, block)} />
            {regimeNarrative(asset, block)}
            <RegimeBubbleChart asset={asset} matches={block.matches} />
          </div>
        ))
      ) : (
        emptyState("No regime matching output was returned for the selected assets.")
      )}
    </div>
  ) : emptyState("Run the Input tab first to populate the historical analog charts.");

  const scenariosTab = response ? (
    <div className="content-stack">
      <div className="panel-hero">
        <div>
          <div className="panel-kicker">Simulation view</div>
          <h2>{selectedTab.label}</h2>
        </div>
        <div className="panel-badge">
          <span>{requestPreview.n_scenarios || 0}</span>
          <small>paths per run</small>
        </div>
      </div>

      {sectionCard("Scenario interpretation", explanation?.sections?.scenario_engine)}

      {scenarioEntries.length ? (
        scenarioEntries.map(([asset, block]) => (
          <div key={asset} className="content-stack asset-section">
            <SummaryKpis items={scenarioMetricItems(asset, block)} />
            {scenarioNarrative(asset, block)}
            <div className="two-col-grid">
              <ScenarioBoxPlot asset={asset} stats={buildTerminalReturnBoxStats(block)} />
              <ScenarioFanChart asset={asset} block={block} />
            </div>
          </div>
        ))
      ) : (
        emptyState("No scenario engine output was returned for the selected assets.")
      )}
    </div>
  ) : emptyState("Run the Input tab first to generate scenario distributions.");

  const riskTab = response ? (
    <div className="content-stack">
      <div className="panel-hero">
        <div>
          <div className="panel-kicker">Allocation and downside</div>
          <h2>{selectedTab.label}</h2>
        </div>
        <div className="panel-badge">
          <span>{portfolioDetails.length}</span>
          <small>portfolio assets</small>
        </div>
      </div>

      <SummaryKpis
        items={[
          { label: "Portfolio return", value: pct(response.portfolio.portfolio_expected_return ?? Number.NaN) },
          { label: "Portfolio CVaR", value: pct(response.portfolio.portfolio_cvar ?? Number.NaN) },
          { label: "Portfolio drawdown", value: pct(response.portfolio.portfolio_max_drawdown_est ?? Number.NaN) },
          { label: "Top weight", value: topWeight ? `${topWeight.symbol} ${pct(topWeight.weight)}` : "-" },
          { label: "Risk tolerance", value: pct(requestPreview.risk_tolerance ?? Number.NaN) }
        ]}
      />

      {sectionCard("Risk and portfolio interpretation", explanation?.sections?.risk_portfolio)}
      {riskNarrative(portfolioDetails, topWeight)}
      <RiskReturnBubbleChart details={portfolioDetails} />
    </div>
  ) : emptyState("Run the Input tab first to calculate risk and portfolio outputs.");

  const contentByTab: Record<TabKey, JSX.Element> = {
    input: inputTab,
    summary: summaryTab,
    regime: regimeTab,
    scenarios: scenariosTab,
    risk: riskTab
  };

  return (
    <>
      <AnalysisLoadingOverlay visible={mutation.isPending} />
      <div className="workspace-shell">
        <aside className="workspace-sidebar">
          <div className="workspace-brand">
            <div className="workspace-mark">AP</div>
            <div>
              <div className="workspace-eyebrow">Agentic dashboard</div>
              <h1>Crypto Return Analysis</h1>
            </div>
          </div>

          <div className="workspace-tab-list">
            {TAB_META.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`workspace-tab ${activeTab === tab.key ? "is-active" : ""}`}
                onClick={() => setActiveTab(tab.key)}
              >
                <span className="workspace-tab-index">{tab.index}</span>
                <span>
                  <strong>{tab.label}</strong>
                </span>
              </button>
            ))}
          </div>

          <Card title="Request snapshot" className="sidebar-note-card">
            <div className="sidebar-note-row">
              <span>Assets</span>
              <strong>{selectedAssetLabels.length}</strong>
            </div>
            <div className="sidebar-note-row">
              <span>Horizon</span>
              <strong>{horizonDays || "-"}</strong>
            </div>
            <div className="sidebar-note-row">
              <span>Scenarios</span>
              <strong>{nScenarios || "-"}</strong>
            </div>
            <div className="sidebar-note-row">
              <span>Risk</span>
              <strong>{riskTolerancePct ? `${riskTolerancePct}%` : "-"}</strong>
            </div>
            <div className="sidebar-note-list">{weightSummary || "Build the request in the Input tab."}</div>
          </Card>
        </aside>

        <section className="workspace-main">
          {contentByTab[activeTab]}
        </section>
      </div>
    </>
  );
}
