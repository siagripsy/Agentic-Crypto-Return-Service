export default function ErrorBanner({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div
      className="card"
      style={{
        borderColor: "rgba(185, 28, 28, 0.18)",
        background: "rgba(254, 242, 242, 0.95)",
        color: "#991b1b"
      }}
    >
      <strong>Error:</strong> {msg}
    </div>
  );
}
