export type ApiCard = {
  id: string;
  title: string;
  details: string;
  due_date: string | null;
  label: string | null;
  priority: string | null;
  created_at: string | null;
  assigned_to: string | null;
};

export type ApiComment = {
  id: string;
  card_id: string;
  username: string;
  content: string;
  created_at: string;
};

export type ApiCardSearchResult = ApiCard & {
  column_id: string;
  column_title: string;
};

export type ApiColumn = {
  id: string;
  title: string;
  wip_limit: number | null;
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

type RequestOptions = { method?: string; body?: unknown };

// Authenticated request against a checked (2xx-or-throw) endpoint. A JSON
// Content-Type header is sent only when a body is provided.
async function request(
  token: string,
  path: string,
  { method, body }: RequestOptions = {},
): Promise<Response> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return checked(res);
}

async function requestJson<T>(
  token: string,
  path: string,
  options?: RequestOptions,
): Promise<T> {
  const res = await request(token, path, options);
  return res.json() as Promise<T>;
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
  return requestJson<ApiBoardSummary[]>(token, "/api/boards");
}

export async function apiCreateBoard(token: string, title: string): Promise<ApiBoardSummary> {
  return requestJson<ApiBoardSummary>(token, "/api/boards", { method: "POST", body: { title } });
}

export async function apiGetBoard(token: string, boardId?: string): Promise<ApiBoard> {
  const url = boardId ? `/api/boards/${boardId}` : "/api/board";
  return requestJson<ApiBoard>(token, url);
}

export async function apiRenameBoard(
  token: string,
  boardId: string,
  title: string,
): Promise<void> {
  await request(token, `/api/boards/${boardId}`, { method: "PUT", body: { title } });
}

export async function apiDeleteBoard(token: string, boardId: string): Promise<void> {
  await request(token, `/api/boards/${boardId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Columns
// ---------------------------------------------------------------------------

export async function apiCreateColumn(
  token: string,
  boardId: string,
  title: string,
): Promise<{ id: string; title: string; position: number }> {
  return requestJson(token, `/api/boards/${boardId}/columns`, {
    method: "POST",
    body: { title },
  });
}

export async function apiRenameColumn(
  token: string,
  columnId: string,
  title: string,
): Promise<void> {
  await request(token, `/api/board/columns/${columnId}`, { method: "PUT", body: { title } });
}

export async function apiDeleteColumn(token: string, columnId: string): Promise<void> {
  await request(token, `/api/board/columns/${columnId}`, { method: "DELETE" });
}

export async function apiMoveColumn(
  token: string,
  columnId: string,
  position: number,
): Promise<void> {
  await request(token, `/api/board/columns/${columnId}/position`, {
    method: "PUT",
    body: { position },
  });
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
  return requestJson<ApiCard>(token, "/api/board/cards", {
    method: "POST",
    body: { column_id: columnId, title, details },
  });
}

export async function apiUpdateCard(
  token: string,
  cardId: string,
  updates: {
    title?: string;
    details?: string;
    due_date?: string | null;
    label?: string | null;
    priority?: string | null;
  },
): Promise<void> {
  await request(token, `/api/board/cards/${cardId}`, { method: "PUT", body: updates });
}

export async function apiArchiveCard(token: string, cardId: string): Promise<void> {
  await request(token, `/api/board/cards/${cardId}/archive`, { method: "POST" });
}

export async function apiUnarchiveCard(token: string, cardId: string): Promise<void> {
  await request(token, `/api/board/cards/${cardId}/unarchive`, { method: "POST" });
}

export async function apiDeleteCard(token: string, cardId: string): Promise<void> {
  await request(token, `/api/board/cards/${cardId}`, { method: "DELETE" });
}

export async function apiSearchCards(
  token: string,
  boardId: string,
  params: { q?: string; label?: string; priority?: string },
): Promise<ApiCardSearchResult[]> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.label) qs.set("label", params.label);
  if (params.priority) qs.set("priority", params.priority);
  return requestJson<ApiCardSearchResult[]>(token, `/api/boards/${boardId}/search?${qs.toString()}`);
}

export async function apiGetArchivedCards(
  token: string,
  boardId: string,
): Promise<ApiCardSearchResult[]> {
  return requestJson<ApiCardSearchResult[]>(token, `/api/boards/${boardId}/archived`);
}

export async function apiSetWipLimit(
  token: string,
  columnId: string,
  wipLimit: number | null,
): Promise<void> {
  await request(token, `/api/board/columns/${columnId}/wip-limit`, {
    method: "PUT",
    body: { wip_limit: wipLimit },
  });
}

export async function apiMoveCard(
  token: string,
  cardId: string,
  columnId: string,
  position: number,
): Promise<void> {
  await request(token, `/api/board/cards/${cardId}/move`, {
    method: "PUT",
    body: { column_id: columnId, position },
  });
}

// ---------------------------------------------------------------------------
// Card comments
// ---------------------------------------------------------------------------

export async function apiGetComments(token: string, cardId: string): Promise<ApiComment[]> {
  return requestJson<ApiComment[]>(token, `/api/board/cards/${cardId}/comments`);
}

export async function apiCreateComment(
  token: string,
  cardId: string,
  content: string,
): Promise<ApiComment> {
  return requestJson<ApiComment>(token, `/api/board/cards/${cardId}/comments`, {
    method: "POST",
    body: { content },
  });
}

export async function apiDeleteComment(token: string, commentId: string): Promise<void> {
  await request(token, `/api/board/comments/${commentId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Board export
// ---------------------------------------------------------------------------

export async function apiExportBoard(token: string, boardId: string): Promise<unknown> {
  return requestJson<unknown>(token, `/api/boards/${boardId}/export`);
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
