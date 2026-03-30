export type ApiBoard = {
  columns: Array<{
    id: string;
    title: string;
    cards: Array<{ id: string; title: string; details: string }>;
  }>;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function authHeaders(token: string): HeadersInit {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

async function checked(res: Response): Promise<Response> {
  if (res.status === 401) throw new ApiError(401, "Unauthorized");
  if (!res.ok) throw new ApiError(res.status, "Request failed");
  return res;
}

export async function apiGetBoard(token: string): Promise<ApiBoard> {
  const res = await checked(
    await fetch("/api/board", { headers: authHeaders(token) }),
  );
  return res.json() as Promise<ApiBoard>;
}

export async function apiRenameColumn(
  token: string,
  columnId: string,
  title: string,
): Promise<void> {
  await checked(
    await fetch(`/api/board/columns/${columnId}`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify({ title }),
    }),
  );
}

export async function apiCreateCard(
  token: string,
  columnId: string,
  title: string,
  details: string,
): Promise<{ id: string; title: string; details: string }> {
  const res = await checked(
    await fetch("/api/board/cards", {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ column_id: columnId, title, details }),
    }),
  );
  return res.json() as Promise<{ id: string; title: string; details: string }>;
}

export async function apiDeleteCard(token: string, cardId: string): Promise<void> {
  await checked(
    await fetch(`/api/board/cards/${cardId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  );
}

export async function apiMoveCard(
  token: string,
  cardId: string,
  columnId: string,
  position: number,
): Promise<void> {
  await checked(
    await fetch(`/api/board/cards/${cardId}/move`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify({ column_id: columnId, position }),
    }),
  );
}

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
