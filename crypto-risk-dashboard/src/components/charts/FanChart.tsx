import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Line } from "recharts";
import Card from "../Card";
import { fanBands } from "../../utils/stats";

export default function FanChart({ paths }: { paths: number[][] | undefined | null }) {
  if (!paths || paths.length === 0) return null;

  const bands = fanBands(paths);
  const data = bands.t.map((t, i) => ({
    t,
    low: bands.pLow[i],
    mid: bands.pMid[i],
    high: bands.pHigh[i]
  }));

  return (
    <Card title="Scenario fan chart (p05–p95 band + median)">
      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <AreaChart data={data}>
            <XAxis dataKey="t" />
            <YAxis />
            <Tooltip />
            {/* band */}
            <Area type="monotone" dataKey="high" stroke="none" fillOpacity={0.15} />
            <Area type="monotone" dataKey="low" stroke="none" fillOpacity={0.15} />
            {/* median */}
            <Line type="monotone" dataKey="mid" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div style={{ marginTop: 8, color: "#666", fontSize: 12 }}>
        X-axis is step (0..H). Values depend on backend engine (often price or return path).
      </div>
    </Card>
  );
}