import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis
} from "recharts";
import Card from "./Card";
import { pct } from "../utils/format";
import { transformPortfolioRiskReturn } from "../utils/cryptoService";
import type { PortfolioDetail } from "../api/types";

const COLORS = ["#0f766e", "#2563eb", "#d97706", "#be123c", "#7c3aed", "#0891b2"];

export default function RiskReturnBubbleChart({ details }: { details: PortfolioDetail[] }) {
  const data = transformPortfolioRiskReturn(details);
  if (!data.length) return null;

  return (
    <div className="two-col-grid">
      <Card title="Risk and return by asset">
        <div className="chart-card">
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 12, right: 16, bottom: 12, left: 12 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="riskMagnitude" name="CVaR magnitude" tickFormatter={(v) => pct(v)} />
              <YAxis type="number" dataKey="expected_return_mean" name="Expected return mean" tickFormatter={(v) => pct(v)} />
              <ZAxis type="number" dataKey="bubbleSize" range={[100, 1200]} />
              <Tooltip
                content={({ active, payload }: any) => {
                  const point = active ? payload?.[0]?.payload : null;
                  if (!point) return null;
                  return (
                    <div className="chart-tooltip">
                      <div><strong>{point.symbol}</strong></div>
                      <div>Weight: {pct(point.weight)}</div>
                      <div>Expected return: {pct(point.expected_return_mean)}</div>
                      <div>Prob. profit: {pct(point.prob_profit)}</div>
                      <div>CVaR: {pct(point.cvar)}</div>
                      <div>Max drawdown: {pct(point.max_drawdown_est)}</div>
                      <div>Score: {point.score.toFixed(4)}</div>
                    </div>
                  );
                }}
              />
              <Scatter data={data}>
                {data.map((entry, index) => (
                  <Cell key={entry.symbol} fill={COLORS[index % COLORS.length]} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <div className="chart-caption">
          Farther right means larger downside tail loss magnitude, higher means stronger expected return, and larger bubbles indicate heavier portfolio weight. Assets in the upper-left region are generally more attractive because they combine lower downside with higher expected return.
        </div>
      </Card>

      <Card title="Suggested portfolio weights">
        <div className="chart-card">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tickFormatter={(v) => pct(v)} />
              <YAxis type="category" dataKey="symbol" width={72} />
              <Tooltip formatter={(value: number) => [pct(value), "Weight"]} />
              <Bar dataKey="weight" radius={[0, 8, 8, 0]}>
                {data.map((entry, index) => (
                  <Cell key={entry.symbol} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
