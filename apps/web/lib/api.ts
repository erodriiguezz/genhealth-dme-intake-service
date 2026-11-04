import type {
  ErrorEnvelope,
  Order,
  OrderList,
  OrderStatus,
  OrderValues,
  TokenResponse,
  User,
} from "./api-types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "dme-intake-token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: unknown = null,
  ) {
    super(message);
  }
}

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // sessionStorage unavailable (private mode): the session lasts until reload.
  }
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

async function request<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, headers, ...rest } = init;
  const h = new Headers(headers);
  const token = auth ? getToken() : null;
  if (token) h.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...rest, headers: h });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.");
  }

  if (res.ok) {
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  let body: Partial<ErrorEnvelope> | null = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  const err = body?.error;
  if (res.status === 401 && auth) {
    setToken(null);
    onUnauthorized?.();
  }
  throw new ApiError(
    res.status,
    err?.code ?? "unknown_error",
    err?.message ?? `Request failed (${res.status}).`,
    err?.details ?? null,
  );
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", { ...json("POST", { email, password }), auth: false }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
      auth: false,
    }),
  me: () => request<User>("/auth/me"),
  listOrders: (status?: OrderStatus) =>
    request<OrderList>(`/orders${status ? `?status=${status}` : ""}`),
  getOrder: (id: string) => request<Order>(`/orders/${encodeURIComponent(id)}`),
  createOrder: (values: Partial<OrderValues>) => request<Order>("/orders", json("POST", values)),
  updateOrder: (id: string, values: Partial<OrderValues>) =>
    request<Order>(`/orders/${encodeURIComponent(id)}`, json("PATCH", values)),
  deleteOrder: (id: string) =>
    request<void>(`/orders/${encodeURIComponent(id)}`, { method: "DELETE" }),
  extractOrder: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Order>("/orders/extract", { method: "POST", body: form });
  },
};
