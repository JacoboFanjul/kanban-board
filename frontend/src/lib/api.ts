const TOKEN_KEY = "pm_auth_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiLogin(username: string, password: string): Promise<string> {
  const res = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  const data = await res.json();
  return data.token as string;
}

export async function apiLogout(token: string): Promise<void> {
  await fetch("/api/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function apiGetMe(token: string): Promise<{ username: string } | null> {
  const res = await fetch("/api/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json() as Promise<{ username: string }>;
}
