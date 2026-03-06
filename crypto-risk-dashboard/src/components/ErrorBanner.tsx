export default function ErrorBanner({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div style={{ padding: 12, borderRadius: 12, border: "1px solid #ffcccc", background: "#fff5f5" }}>
      <b>Error:</b> {msg}
    </div>
  );
}