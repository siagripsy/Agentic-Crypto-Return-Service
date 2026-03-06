export default function Card({
  title,
  children
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        border: "1px solid #e9e9e9",
        borderRadius: 14,
        padding: 14,
        background: "white",
        boxShadow: "0 1px 10px rgba(0,0,0,0.03)"
      }}
    >
      {title ? <div style={{ fontWeight: 700, marginBottom: 10 }}>{title}</div> : null}
      {children}
    </div>
  );
}