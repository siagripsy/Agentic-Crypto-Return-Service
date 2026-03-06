export default function JsonPanel({ data }: { data: any }) {
  if (!data) return <div style={{ color: "#666" }}>—</div>;
  return (
    <pre
      style={{
        margin: 0,
        padding: 12,
        borderRadius: 12,
        background: "#0b0b0b",
        color: "white",
        overflow: "auto",
        maxHeight: 280
      }}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}