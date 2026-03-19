export interface SummaryKpi {
  label: string;
  value: string;
}

export default function SummaryKpis({ items }: { items: SummaryKpi[] }) {
  return (
    <div className="kpi-grid">
      {items.map((item) => (
        <div key={item.label} className="kpi-card">
          <div className="kpi-label">{item.label}</div>
          <div className="kpi-value">{item.value}</div>
        </div>
      ))}
    </div>
  );
}
