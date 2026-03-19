const AUTH_KEY = "crypto-risk-dashboard-auth";

export function isAuthenticated(): boolean {
  return localStorage.getItem(AUTH_KEY) === "true";
}

export function login(username: string, password: string): boolean {
  const ok = username === "admin" && password === "admin";
  if (ok) {
    localStorage.setItem(AUTH_KEY, "true");
  }
  return ok;
}

export function logout(): void {
  localStorage.removeItem(AUTH_KEY);
}
