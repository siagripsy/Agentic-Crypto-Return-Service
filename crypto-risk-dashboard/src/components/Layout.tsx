import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-title">Agentic Probabilistic Crypto Return Service — Dashboard</div>

        <nav className="app-nav">
          <NavLink
            to="/forecast"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            Forecast
          </NavLink>
          <NavLink
            to="/portfolio"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            Portfolio
          </NavLink>
        </nav>
      </header>

      <main className="page-wrap">
        <Outlet />
      </main>
    </div>
  );
}