import Card from "../Card";
import { pct } from "../../utils/format";

function normalPdf(x: number, mu: number, sigma: number) {
  const z = (x - mu) / sigma;
  return Math.exp(-0.5 * z * z) / (sigma * Math.sqrt(2 * Math.PI));
}

export default function ReturnDistributionHistogram({
  p05,
  median,
  p95,
  mean
}: {
  p05?: number;
  median?: number;
  p95?: number;
  mean?: number;
}) {
  if (!Number.isFinite(p05) || !Number.isFinite(median) || !Number.isFinite(p95)) {
    return null;
  }

  const q05 = p05!;
  const q50 = median!;
  const q95 = p95!;
  const mu = Number.isFinite(mean) ? mean! : q50;

  // Approximate sigma assuming roughly normal quantiles:
  // p95 ≈ mu + 1.645*sigma, p05 ≈ mu - 1.645*sigma
  const sigma = Math.max((q95 - q05) / (2 * 1.645), 1e-6);

  const minX = q05 - 0.5 * (q95 - q05);
  const maxX = q95 + 0.5 * (q95 - q05);

  const n = 60;
  const points = Array.from({ length: n }, (_, i) => {
    const x = minX + (i / (n - 1)) * (maxX - minX);
    const y = normalPdf(x, mu, sigma);
    return { x, y };
  });

  const maxY = Math.max(...points.map((p) => p.y), 1);

  const svgWidth = 1000;
  const svgHeight = 180;
  const padding = 24;

  const sx = (x: number) =>
    padding + ((x - minX) / (maxX - minX)) * (svgWidth - 2 * padding);

  const sy = (y: number) =>
    svgHeight - padding - (y / maxY) * (svgHeight - 2 * padding);

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${sx(p.x)} ${sy(p.y)}`)
    .join(" ");

  const areaD =
    `${pathD} L ${sx(points[points.length - 1].x)} ${svgHeight - padding} ` +
    `L ${sx(points[0].x)} ${svgHeight - padding} Z`;

  const markerStyle = (x: number, color: string, dash = false) => ({
    x1: sx(x),
    x2: sx(x),
    y1: padding,
    y2: svgHeight - padding,
    stroke: color,
    strokeWidth: 2,
    strokeDasharray: dash ? "5 4" : undefined
  });

  return (
    <Card title="Horizon return distribution">
      <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>
        Approximate distribution reconstructed from p05 / median / p95 summary statistics
      </div>

      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: "100%", height: 220 }}>
        <path d={areaD} fill="#e9e9e9" />
        <path d={pathD} fill="none" stroke="#111" strokeWidth="3" />

        <line {...markerStyle(q05, "#999", true)} />
        <line {...markerStyle(q50, "#111", false)} />
        <line {...markerStyle(q95, "#999", true)} />
        <line {...markerStyle(mu, "#666", true)} />

        <text x={sx(q05)} y={svgHeight - 4} textAnchor="middle" fontSize="16" fill="#666">
          p05
        </text>
        <text x={sx(q50)} y={svgHeight - 4} textAnchor="middle" fontSize="16" fill="#111">
          median
        </text>
        <text x={sx(q95)} y={svgHeight - 4} textAnchor="middle" fontSize="16" fill="#666">
          p95
        </text>
      </svg>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginTop: 8 }}>
        <div>
          <div style={{ fontSize: 12, color: "#666" }}>p05</div>
          <div style={{ fontWeight: 700 }}>{pct(q05)}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "#666" }}>median</div>
          <div style={{ fontWeight: 700 }}>{pct(q50)}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "#666" }}>p95</div>
          <div style={{ fontWeight: 700 }}>{pct(q95)}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "#666" }}>mean</div>
          <div style={{ fontWeight: 700 }}>{pct(mu)}</div>
        </div>
      </div>
    </Card>
  );
}