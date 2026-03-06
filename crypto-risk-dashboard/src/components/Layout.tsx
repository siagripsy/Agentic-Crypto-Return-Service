import { Link, useLocation } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  const loc = useLocation();

  const navItem = (to: string, label: string) => {
    const active = loc.pathname === to;
    return (
      <Link
        to={to}
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          textDecoration: "none",
          color: active ? "white" : "#111",
          background: active ? "#111" : "transparent",
          border: "1px solid #ddd"
        }}
      >
        {label}
      </Link>
    );
  };

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 20px",
          borderBottom: "1px solid #eee",
          position: "sticky",
          top: 0,
          background: "white",
          zIndex: 20
        }}
      >
        <div style={{ fontWeight: 800 }}>Agentic Probabilistic Crypto Return Service — Dashboard</div>
        <nav style={{ display: "flex", gap: 10 }}>
          {navItem("/forecast", "Forecast")}
          {navItem("/portfolio", "Portfolio")}
        </nav>
      </header>

      <main style={{ padding: 20, maxWidth: 1250, margin: "0 auto" }}>{children}</main>
    </div>
  );
}