import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { logout } from "../utils/auth";

export default function Layout() {
  const navigate = useNavigate();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <div className="eyebrow">Dashboard</div>
          <div className="app-title">Agentic Probabilistic Crypto Return Service</div>
        </div>

        <nav className="app-nav">
          <NavLink to="/crypto-service" className={({ isActive }) => (isActive ? "active" : "")}>
            Workspace
          </NavLink>
          <button
            type="button"
            className="ghost-btn"
            onClick={() => {
              logout();
              navigate("/login", { replace: true });
            }}
          >
            Logout
          </button>
        </nav>
      </header>

      <main className="page-wrap">
        <Outlet />
      </main>
    </div>
  );
}
