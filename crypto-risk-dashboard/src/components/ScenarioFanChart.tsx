import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import Card from "./Card";
import { buildFanChartBands } from "../utils/cryptoService";
import { num } from "../utils/format";
import type { ScenarioEngineBlock } from "../api/types";

export default function ScenarioFanChart({
  asset,
  block
}: {
  asset: string;
  block: ScenarioEngineBlock;
}) {
  const data = buildFanChartBands(block);
  const enriched = data.map((row) => ({
    ...row,
    band90Low: row.p10,
    band90High: row.p90 - row.p10,
    band50Low: row.p25,
    band50High: row.p75 - row.p25
  }));

  return (
    <Card title={`${asset} scenario fan chart`}>
      <div className="chart-card">
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={enriched} margin={{ top: 10, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="day" />
            <YAxis tickFormatter={(value) => num(value, 2)} />
            <Tooltip
              content={({ active, payload, label }: any) => {
                if (!active || !payload?.length) return null;
                const row = payload[0].payload;
                return (
                  <div className="chart-tooltip">
                    <div><strong>Day {label}</strong></div>
                    <div>P10: {num(row.p10, 2)}</div>
                    <div>P25: {num(row.p25, 2)}</div>
                    <div>Median: {num(row.p50, 2)}</div>
                    <div>P75: {num(row.p75, 2)}</div>
                    <div>P90: {num(row.p90, 2)}</div>
                  </div>
                );
              }}
            />
            <Area type="monotone" dataKey="band90Low" stackId="outer" stroke="none" fill="transparent" />
            <Area type="monotone" dataKey="band90High" stackId="outer" stroke="none" fill="#bfdbfe" />
            <Area type="monotone" dataKey="band50Low" stackId="inner" stroke="none" fill="transparent" />
            <Area type="monotone" dataKey="band50High" stackId="inner" stroke="none" fill="#60a5fa" />
            <Line type="monotone" dataKey="p50" stroke="#1d4ed8" dot={false} strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-caption">
        This chart shows a range of possible future price paths. The darker middle band is the more typical range, while the outer bands show wider uncertainty.
      </div>
    </Card>
  );
}
