export default function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div style={{ padding: 12, border: "1px dashed #ccc", borderRadius: 12 }}>
      {label}
    </div>
  );
}