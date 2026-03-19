import JsonPanel from "./JsonPanel";

export default function CollapsibleJsonPanel({
  title,
  data,
  defaultOpen = false
}: {
  title: string;
  data: unknown;
  defaultOpen?: boolean;
}) {
  return (
    <details className="collapsible-panel" open={defaultOpen}>
      <summary>{title}</summary>
      <div className="json-panel">
        <JsonPanel data={data} />
      </div>
    </details>
  );
}
