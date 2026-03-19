import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Card from "../components/Card";
import { login } from "../utils/auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || "/crypto-service";

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (login(username.trim(), password)) {
      navigate(from, { replace: true });
      return;
    }
    setError("Invalid credentials. Use admin / admin.");
  }

  return (
    <div className="login-shell">
      <div className="login-hero">
        <div className="eyebrow">Secure Access</div>
        <h1>Agentic Crypto Return Service</h1>
        <p>
          Sign in to open the combined analysis workflow with regime matching, scenario simulation,
          portfolio risk, and explanation cards in one place.
        </p>
      </div>

      <Card title="Login">
        <form className="form-grid" onSubmit={onSubmit}>
          <label className="form-group">
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label className="form-group">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error ? <div className="field-error">{error}</div> : null}
          <button className="primary-btn" type="submit">
            Sign in
          </button>
          <div className="helper-text">Demo credentials: admin / admin</div>
        </form>
      </Card>
    </div>
  );
}
