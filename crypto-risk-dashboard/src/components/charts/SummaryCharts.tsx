import Card from "../Card";
import { pct, num } from "../../utils/format";
import ReturnDistributionHistogram from "./ReturnDistributionHistogram";

type SummaryBlock = {
  n_scenarios?: number;
  horizon_days?: number;
  terminal_price_summary?: {
    mean?: number;
    median?: number;
    p05?: number;
    p95?: number;
  };
  horizon_return_summary?: {
    mean?: number;
    median?: number;
    p05?: number;
    p95?: number;
  };
  prob_profit?: number;
  prob_loss?: number;
  VaR_CVaR_horizon_return?: {
    VaR?: number;
    CVaR?: number;
  };
  max_drawdown_summary?: {
    mean?: number;
    median?: number;
    p05?: number;
    p95?: number;
  };
  VaR_CVaR_max_drawdown?: {
    VaR?: number;
    CVaR?: number;
  };
  profit_analysis?: {
    count?: number;
    mean_profit?: number;
    max_profit?: number;
    min_profit?: number;
    mean_max_drawdown?: number;
  };
  loss_analysis?: {
    count?: number;
    mean_loss?: number;
    worst_loss?: number;
    smallest_loss?: number;
  };
};

function RangeBar({
  title,
  low,
  mid,
  high,
  formatter,
  subtitle
}: {
  title: string;
  low?: number;
  mid?: number;
  high?: number;
  formatter: (x: number) => string;
  subtitle?: string;
}) {
  const vals = [low, mid, high].filter((v): v is number => Number.isFinite(v));
  if (vals.length === 0) return null;

  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;

  const pctPos = (v?: number) => {
    if (!Number.isFinite(v)) return 0;
    return ((v! - min) / span) * 100;
  };

  return (
    <Card title={title}>
      <div style={{ color: "#666", fontSize: 12, marginBottom: 10 }}>{subtitle ?? "p05 / median / p95"}</div>

      <div style={{ position: "relative", height: 18, borderRadius: 999, background: "#f1f1f1", marginBottom: 14 }}>
        <div
          style={{
            position: "absolute",
            left: `${pctPos(low)}%`,
            width: `${Math.max(2, pctPos(high) - pctPos(low))}%`,
            top: 0,
            bottom: 0,
            borderRadius: 999,
            background: "#d9d9d9"
          }}
        />
        <div
          style={{
            position: "absolute",
            left: `calc(${pctPos(mid)}% - 2px)`,
            width: 4,
            top: -4,
            bottom: -4,
            borderRadius: 4,
            background: "#111"
          }}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
        <div>
          <div style={{ color: "#666", fontSize: 12 }}>p05</div>
          <div style={{ fontWeight: 700 }}>{Number.isFinite(low) ? formatter(low!) : "—"}</div>
        </div>
        <div>
          <div style={{ color: "#666", fontSize: 12 }}>median</div>
          <div style={{ fontWeight: 700 }}>{Number.isFinite(mid) ? formatter(mid!) : "—"}</div>
        </div>
        <div>
          <div style={{ color: "#666", fontSize: 12 }}>p95</div>
          <div style={{ fontWeight: 700 }}>{Number.isFinite(high) ? formatter(high!) : "—"}</div>
        </div>
      </div>
    </Card>
  );
}

function StackedProbBar({ profit, loss }: { profit?: number; loss?: number }) {
  if (!Number.isFinite(profit) && !Number.isFinite(loss)) return null;

  const p = Math.max(0, Math.min(1, profit ?? 0));
  const l = Math.max(0, Math.min(1, loss ?? 0));

  return (
    <Card title="Outcome probability">
      <div style={{ color: "#666", fontSize: 12, marginBottom: 10 }}>Probability of finishing profit vs loss</div>
      <div style={{ display: "flex", height: 22, borderRadius: 999, overflow: "hidden", border: "1px solid #ddd" }}>
        <div style={{ width: `${p * 100}%`, background: "#111" }} />
        <div style={{ width: `${l * 100}%`, background: "#d9d9d9" }} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 12 }}>
        <div>
          <div style={{ color: "#666", fontSize: 12 }}>Prob. profit</div>
          <div style={{ fontWeight: 700 }}>{pct(p)}</div>
        </div>
        <div>
          <div style={{ color: "#666", fontSize: 12 }}>Prob. loss</div>
          <div style={{ fontWeight: 700 }}>{pct(l)}</div>
        </div>
      </div>
    </Card>
  );
}

function RiskCards({
  retRisk,
  ddRisk
}: {
  retRisk?: { VaR?: number; CVaR?: number };
  ddRisk?: { VaR?: number; CVaR?: number };
}) {
  return (
    <Card title="Tail risk summary">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
          <div style={{ color: "#666", fontSize: 12 }}>Return VaR</div>
          <div style={{ fontWeight: 800 }}>{Number.isFinite(retRisk?.VaR) ? pct(retRisk!.VaR!) : "—"}</div>
        </div>
        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
          <div style={{ color: "#666", fontSize: 12 }}>Return CVaR</div>
          <div style={{ fontWeight: 800 }}>{Number.isFinite(retRisk?.CVaR) ? pct(retRisk!.CVaR!) : "—"}</div>
        </div>
        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
          <div style={{ color: "#666", fontSize: 12 }}>Drawdown VaR</div>
          <div style={{ fontWeight: 800 }}>{Number.isFinite(ddRisk?.VaR) ? pct(ddRisk!.VaR!) : "—"}</div>
        </div>
        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
          <div style={{ color: "#666", fontSize: 12 }}>Drawdown CVaR</div>
          <div style={{ fontWeight: 800 }}>{Number.isFinite(ddRisk?.CVaR) ? pct(ddRisk!.CVaR!) : "—"}</div>
        </div>
      </div>
    </Card>
  );
}

function ProfitLossDetail({
  profitAnalysis,
  lossAnalysis
}: {
  profitAnalysis?: SummaryBlock["profit_analysis"];
  lossAnalysis?: SummaryBlock["loss_analysis"];
}) {
  return (
    <Card title="Profit / loss detail">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Winning scenarios</div>
          <div style={{ color: "#666", fontSize: 12 }}>Count</div>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>{profitAnalysis?.count ?? "—"}</div>

          <div style={{ color: "#666", fontSize: 12 }}>Mean profit</div>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>
            {Number.isFinite(profitAnalysis?.mean_profit) ? pct(profitAnalysis!.mean_profit!) : "—"}
          </div>

          <div style={{ color: "#666", fontSize: 12 }}>Max profit</div>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>
            {Number.isFinite(profitAnalysis?.max_profit) ? pct(profitAnalysis!.max_profit!) : "—"}
          </div>

          <div style={{ color: "#666", fontSize: 12 }}>Mean max drawdown</div>
          <div style={{ fontWeight: 700 }}>
            {Number.isFinite(profitAnalysis?.mean_max_drawdown) ? pct(profitAnalysis!.mean_max_drawdown!) : "—"}
          </div>
        </div>

        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Losing scenarios</div>
          <div style={{ color: "#666", fontSize: 12 }}>Count</div>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>{lossAnalysis?.count ?? "—"}</div>

          <div style={{ color: "#666", fontSize: 12 }}>Mean loss</div>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>
            {Number.isFinite(lossAnalysis?.mean_loss) ? pct(lossAnalysis!.mean_loss!) : "—"}
          </div>

          <div style={{ color: "#666", fontSize: 12 }}>Worst loss</div>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>
            {Number.isFinite(lossAnalysis?.worst_loss) ? pct(lossAnalysis!.worst_loss!) : "—"}
          </div>

          <div style={{ color: "#666", fontSize: 12 }}>Smallest loss</div>
          <div style={{ fontWeight: 700 }}>
            {Number.isFinite(lossAnalysis?.smallest_loss) ? pct(lossAnalysis!.smallest_loss!) : "—"}
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function SummaryCharts({
  block,
  label
}: {
  block?: SummaryBlock | null;
  label: string;
}) {
  if (!block) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Card title={`${label} summary`}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
            <div style={{ color: "#666", fontSize: 12 }}>Scenarios</div>
            <div style={{ fontWeight: 800 }}>{block.n_scenarios ?? "—"}</div>
          </div>
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
            <div style={{ color: "#666", fontSize: 12 }}>Horizon days</div>
            <div style={{ fontWeight: 800 }}>{block.horizon_days ?? "—"}</div>
          </div>
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
            <div style={{ color: "#666", fontSize: 12 }}>Mean terminal price</div>
            <div style={{ fontWeight: 800 }}>
              {Number.isFinite(block.terminal_price_summary?.mean) ? num(block.terminal_price_summary!.mean!) : "—"}
            </div>
          </div>
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
            <div style={{ color: "#666", fontSize: 12 }}>Median return</div>
            <div style={{ fontWeight: 800 }}>
              {Number.isFinite(block.horizon_return_summary?.median) ? pct(block.horizon_return_summary!.median!) : "—"}
            </div>
          </div>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>

        <RangeBar
            title="Terminal price interval"
            subtitle="p05 / median / p95 terminal price"
            low={block.terminal_price_summary?.p05}
            mid={block.terminal_price_summary?.median}
            high={block.terminal_price_summary?.p95}
            formatter={(x) => num(x, 2)}
        />

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

            <RangeBar
            title="Horizon return interval"
            subtitle="p05 / median / p95 horizon return"
            low={block.horizon_return_summary?.p05}
            mid={block.horizon_return_summary?.median}
            high={block.horizon_return_summary?.p95}
            formatter={(x) => pct(x)}
            />

            <ReturnDistributionHistogram
            p05={block.horizon_return_summary?.p05}
            median={block.horizon_return_summary?.median}
            p95={block.horizon_return_summary?.p95}
            mean={block.horizon_return_summary?.mean}
            />

        </div>

      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <StackedProbBar profit={block.prob_profit} loss={block.prob_loss} />
        <RiskCards
          retRisk={block.VaR_CVaR_horizon_return}
          ddRisk={block.VaR_CVaR_max_drawdown}
        />
      </div>

      <RangeBar
        title="Max drawdown interval"
        subtitle="p05 / median / p95 max drawdown"
        low={block.max_drawdown_summary?.p05}
        mid={block.max_drawdown_summary?.median}
        high={block.max_drawdown_summary?.p95}
        formatter={(x) => pct(x)}
      />

      <ProfitLossDetail
        profitAnalysis={block.profit_analysis}
        lossAnalysis={block.loss_analysis}
      />
    </div>
  );
}