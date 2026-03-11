import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import Card from "../Card";

/**
 * Supports either:
 * - fast_regime_fixed: response.risk = { "var_0.05": x, "cvar_0.05": y, ... } (approx)
 * - path engines: response.risk_curve_metrics = { "0.05": { var:..., cvar:... }, ... } (varies)
 *
 * We keep it flexible and best-effort.
 */
export default function RiskCurve({
  risk,
  riskCurveMetrics
}: {
  risk?: Record<string, any> | null;
  riskCurveMetrics?: Record<string, any> | null;
}) {
  const rows: { alpha: number; var?: number; cvar?: number }[] = [];

  if (riskCurveMetrics && typeof riskCurveMetrics === "object") {
    for (const [k, v] of Object.entries(riskCurveMetrics)) {
      const a = Number(k);
      if (!Number.isFinite(a)) continue;
      const vv: any = v;
      rows.push({ alpha: a, var: vv?.var ?? vv?.VaR, cvar: vv?.cvar ?? vv?.CVaR });
    }
  } else if (risk && typeof risk === "object") {
    // Try to parse keys like "var_0.05" / "cvar_0.05"
    const byAlpha: Record<number, { alpha: number; var?: number; cvar?: number }> = {};
    for (const [k, v] of Object.entries(risk)) {
      const m = k.match(/(var|cvar)[^\d]*([0-9.]+)/i);
      if (!m) continue;
      const typ = m[1].toLowerCase();
      const a = Number(m[2]);
      if (!Number.isFinite(a)) continue;
      byAlpha[a] = byAlpha[a] ?? { alpha: a };
      (byAlpha[a] as any)[typ] = Number(v);
    }
    rows.push(...Object.values(byAlpha));
  }

  const data = rows.sort((a, b) => a.alpha - b.alpha);
  if (data.length === 0) return null;

  return (
    <Card title="Risk curve (VaR / CVaR vs alpha)">
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <LineChart data={data}>
            <XAxis dataKey="alpha" tickFormatter={(x) => Number(x).toFixed(2)} />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="var" dot={false} />
            <Line type="monotone" dataKey="cvar" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}