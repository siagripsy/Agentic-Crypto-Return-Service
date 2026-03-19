export default function JsonPanel({ data }: { data: any }) {
  if (!data) return <div style={{ color: "#64748b" }}>No data</div>;
  return (
    <pre
      style={{
        margin: 0,
        padding: 14,
        borderRadius: 14,
        background: "#0f172a",
        color: "#e2e8f0",
        overflow: "auto",
        maxHeight: 360,
        fontSize: 12
      }}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
