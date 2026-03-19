import Card from "./Card";
import { pct } from "../utils/format";

type BoxStats = { min: number; q1: number; median: number; q3: number; max: number };

function position(value: number, min: number, span: number) {
  return ((value - min) / span) * 100;
}

export default function ScenarioBoxPlot({
  asset,
  stats
}: {
  asset: string;
  stats: BoxStats | null;
}) {
  if (!stats) return null;

  const values = [stats.min, stats.q1, stats.median, stats.q3, stats.max];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const zeroInside = min <= 0 && max >= 0;

  const markers = [
    { label: "Min", value: stats.min },
    { label: "Q1", value: stats.q1 },
    { label: "Median", value: stats.median },
    { label: "Q3", value: stats.q3 },
    { label: "Max", value: stats.max }
  ];

  return (
    <Card title={`${asset} terminal return distribution`} className="distribution-card">
      <div className="box-plot-header">
        <div>
          <div className="metric-chip-label">Interquartile range</div>
          <div className="metric-chip-value">{pct(stats.q3 - stats.q1)}</div>
        </div>
        <div>
          <div className="metric-chip-label">Median return</div>
          <div className="metric-chip-value">{pct(stats.median)}</div>
        </div>
        <div>
          <div className="metric-chip-label">Full range</div>
          <div className="metric-chip-value">
            {pct(stats.min)} to {pct(stats.max)}
          </div>
        </div>
      </div>

      <div className="distribution-rail">
        <div className="distribution-track" />
        {zeroInside ? (
          <div
            className="distribution-zero"
            style={{ left: `${position(0, min, span)}%` }}
            aria-hidden="true"
          />
        ) : null}
        <div
          className="distribution-whisker"
          style={{
            left: `${position(stats.min, min, span)}%`,
            width: `${Math.max(position(stats.max, min, span) - position(stats.min, min, span), 1)}%`
          }}
        />
        <div
          className="distribution-box"
          style={{
            left: `${position(stats.q1, min, span)}%`,
            width: `${Math.max(position(stats.q3, min, span) - position(stats.q1, min, span), 3)}%`
          }}
        />
        <div
          className="distribution-median"
          style={{ left: `${position(stats.median, min, span)}%` }}
        />

        {markers.map((marker) => (
          <div
            key={marker.label}
            className="distribution-marker"
            style={{ left: `${position(marker.value, min, span)}%` }}
          >
            <span>{marker.label}</span>
            <strong>{pct(marker.value)}</strong>
          </div>
        ))}
      </div>

      <div className="distribution-scale">
        <span>{pct(min)}</span>
        {zeroInside ? <span>0%</span> : <span>{pct((min + max) / 2)}</span>}
        <span>{pct(max)}</span>
      </div>

      <div className="chart-caption">
        The box shows the middle 50% of terminal returns, the whiskers show the full simulated range, and the vertical median line highlights the center of the distribution.
      </div>
    </Card>
  );
}
