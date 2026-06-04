export type ApiCard = {
  id: string;
  title: string;
  details: string;
  due_date: string | null;
  label: string | null;
};

export type ApiColumn = {
  id: string;
  title: string;
  cards: ApiCard[];
};

export type ApiBoard = {
  id: string;
  title: string;
  columns: ApiColumn[];
};

export type ApiBoardSummary = {
  id: string;
  title: string;
  created_at: string;
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

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

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

export async function apiRegister(
  username: string,
  password: string,
  email?: string,
): Promise<string> {
  const res = await fetch("/api/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, email }),
  });
  if (res.status === 409) throw new ApiError(409, "Username already taken");
  if (res.status === 422) {
    const data = await res.json();
    throw new ApiError(422, data.detail ?? "Validation error");
  }
  if (!res.ok) throw new Error("Registration failed");
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

export async function apiChangePassword(
  token: string,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const res = await fetch("/api/me/password", {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (res.status === 401) throw new ApiError(401, "Current password is incorrect");
  if (res.status === 422) {
    const data = await res.json();
    throw new ApiError(422, data.detail ?? "Validation error");
  }
  if (!res.ok) throw new Error("Failed to change password");
}

// ---------------------------------------------------------------------------
// Boards
// ---------------------------------------------------------------------------

export async function apiListBoards(token: string): Promise<ApiBoardSummary[]> {
  const res = await checked(await fetch("/api/boards", { headers: authHeaders(token) }));
  return res.json() as Promise<ApiBoardSummary[]>;
}

export async function apiCreateBoard(token: string, title: string): Promise<ApiBoardSummary> {
  const res = await checked(
    await fetch("/api/boards", {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ title }),
    }),
  );
  return res.json() as Promise<ApiBoardSummary>;
}

export async function apiGetBoard(token: string, boardId?: string): Promise<ApiBoard> {
  const url = boardId ? `/api/boards/${boardId}` : "/api/board";
  const res = await checked(await fetch(url, { headers: authHeaders(token) }));
  return res.json() as Promise<ApiBoard>;
}

export async function apiRenameBoard(
  token: string,
  boardId: string,
  title: string,
): Promise<void> {
  await checked(
    await fetch(`/api/boards/${boardId}`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify({ title }),
    }),
  );
}

export async function apiDeleteBoard(token: string, boardId: string): Promise<void> {
  await checked(
    await fetch(`/api/boards/${boardId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  );
}

// ---------------------------------------------------------------------------
// Columns
// ---------------------------------------------------------------------------

export async function apiCreateColumn(
  token: string,
  boardId: string,
  title: string,
): Promise<{ id: string; title: string; position: number }> {
  const res = await checked(
    await fetch(`/api/boards/${boardId}/columns`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ title }),
    }),
  );
  return res.json() as Promise<{ id: string; title: string; position: number }>;
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

export async function apiDeleteColumn(token: string, columnId: string): Promise<void> {
  await checked(
    await fetch(`/api/board/columns/${columnId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  );
}

export async function apiMoveColumn(
  token: string,
  columnId: string,
  position: number,
): Promise<void> {
  await checked(
    await fetch(`/api/board/columns/${columnId}/position`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify({ position }),
    }),
  );
}

// ---------------------------------------------------------------------------
// Cards
// ---------------------------------------------------------------------------

export async function apiCreateCard(
  token: string,
  columnId: string,
  title: string,
  details: string,
): Promise<ApiCard> {
  const res = await checked(
    await fetch("/api/board/cards", {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ column_id: columnId, title, details }),
    }),
  );
  return res.json() as Promise<ApiCard>;
}

export async function apiUpdateCard(
  token: string,
  cardId: string,
  updates: { title?: string; details?: string; due_date?: string | null; label?: string | null },
): Promise<void> {
  await checked(
    await fetch(`/api/board/cards/${cardId}`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify(updates),
    }),
  );
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

// ---------------------------------------------------------------------------
// Local storage
// ---------------------------------------------------------------------------

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
