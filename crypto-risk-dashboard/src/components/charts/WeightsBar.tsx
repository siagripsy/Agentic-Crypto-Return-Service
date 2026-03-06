import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import Card from "../Card";

export default function WeightsBar({ weights }: { weights: Record<string, number> | undefined | null }) {
  if (!weights) return null;
  const data = Object.entries(weights)
    .map(([k, v]) => ({ asset: k, weight: v }))
    .sort((a, b) => b.weight - a.weight);

  return (
    <Card title="Portfolio weights">
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={data}>
            <XAxis dataKey="asset" />
            <YAxis tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`} />
            <Tooltip formatter={(v) => `${(Number(v) * 100).toFixed(2)}%`} />
            <Bar dataKey="weight" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}