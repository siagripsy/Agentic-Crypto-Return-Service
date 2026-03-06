import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import Card from "../Card";
import { histogram } from "../../utils/stats";

export default function Histogram({
  values,
  title = "Distribution"
}: {
  values: number[] | undefined | null;
  title?: string;
}) {
  if (!values || values.length === 0) return null;

  const { edges, counts, step } = histogram(values, 40);
  const data = edges.map((x, i) => ({ x: x, count: counts[i] ?? 0 }));

  return (
    <Card title={title}>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={data}>
            <XAxis
              dataKey="x"
              tickFormatter={(v) => (typeof v === "number" ? v.toFixed(2) : String(v))}
            />
            <YAxis />
            <Tooltip
              formatter={(val) => val as any}
              labelFormatter={(label) => `bin start: ${Number(label).toFixed(4)} (w=${step?.toFixed(4)})`}
            />
            <Bar dataKey="count" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}