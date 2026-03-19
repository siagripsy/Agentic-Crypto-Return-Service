import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis
} from "recharts";
import Card from "./Card";
import { pct, num } from "../utils/format";
import { transformRegimeMatches } from "../utils/cryptoService";
import type { RegimeMatch } from "../api/types";

function regimeBubbleColor(value: number) {
  const clamped = Math.max(-0.2, Math.min(0.2, value));
  if (clamped >= 0) {
    const strength = clamped / 0.2;
    const red = Math.round(214 - strength * 74);
    const green = Math.round(88 + strength * 92);
    const blue = Math.round(80 - strength * 24);
    return `rgb(${red}, ${green}, ${blue})`;
  }
  const strength = Math.abs(clamped) / 0.2;
  const red = Math.round(180 + strength * 38);
  const green = Math.round(74 - strength * 34);
  const blue = Math.round(76 - strength * 28);
  return `rgb(${red}, ${green}, ${blue})`;
}

export default function RegimeBubbleChart({
  asset,
  matches
}: {
  asset: string;
  matches: RegimeMatch[];
}) {
  const data = transformRegimeMatches(asset, matches);

  return (
    <Card title={`${asset} regime matches`}>
      <div className="chart-card">
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart margin={{ top: 10, right: 16, bottom: 10, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(108, 117, 142, 0.18)" />
            <XAxis type="number" dataKey="similarity" name="Similarity" domain={["dataMin", "dataMax"]} />
            <YAxis type="number" dataKey="profit_pct" name="Forward profit %" tickFormatter={(v) => pct(v)} />
            <ReferenceLine y={0} stroke="#f59e0b" strokeWidth={2} strokeDasharray="7 5" />
            <ZAxis type="number" dataKey="drawdownSize" range={[100, 1000]} />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === "profit_pct") return [pct(value), "Forward profit"];
                if (name === "similarity") return [num(value, 4), "Similarity"];
                return [num(value, 2), name];
              }}
              content={({ active, payload }: any) => {
                const point = active ? payload?.[0]?.payload : null;
                if (!point) return null;
                return (
                  <div className="chart-tooltip">
                    <div><strong>{point.asset}</strong></div>
                    <div>Rank: {point.rank}</div>
                    <div>Window: {point.window_start_date} to {point.window_end_date}</div>
                    <div>Forward end: {point.forward_end_date}</div>
                    <div>Similarity: {num(point.similarity, 4)}</div>
                    <div>Profit: {pct(point.profit_pct)}</div>
                    <div>Max drawdown: {pct(point.max_drawdown_pct)}</div>
                  </div>
                );
              }}
            />
            <Scatter data={data}>
              {data.map((entry, index) => (
                <Cell key={`${entry.asset}-${entry.rank}-${index}`} fill={regimeBubbleColor(entry.profit_pct)} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-caption">
        The amber line marks 0% forward return so profitable and loss-making historical analogs are easier to separate. Points farther right are more similar, and larger bubbles indicate deeper drawdowns.
      </div>
    </Card>
  );
}
