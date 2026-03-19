export default function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="card" style={{ borderStyle: "dashed", color: "#64748b" }}>
      {label}
    </div>
  );
}
