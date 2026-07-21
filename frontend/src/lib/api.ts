const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

let accessToken: string | null = null;
let refreshPromise: Promise<boolean> | null = null;

export const tokenStore = {
  get access() {
    return accessToken;
  },
  set(access: string) {
    accessToken = access;
  },
  clear() {
    accessToken = null;
  },
};

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (tokenStore.access) headers["Authorization"] = `Bearer ${tokenStore.access}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers, credentials: "include" });

  if (res.status === 401 && retry && path !== "/auth/refresh") {
    const refreshed = await tryRefresh();
    if (refreshed) return request<T>(path, options, false);
  }

  if (!res.ok) {
    const problem = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(problem.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
        });
        if (!res.ok) return false;
        const data = await res.json();
        tokenStore.set(data.access_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function download(path: string, filename: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (tokenStore.access) headers.Authorization = `Bearer ${tokenStore.access}`;
  let response = await fetch(`${BASE}${path}`, { headers, credentials: "include" });
  if (response.status === 401 && (await tryRefresh())) {
    headers.Authorization = `Bearer ${tokenStore.access}`;
    response = await fetch(`${BASE}${path}`, { headers, credentials: "include" });
  }
  if (!response.ok) {
    const problem = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(problem.detail ?? "Export failed");
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  download,
  refreshSession: tryRefresh,
  logout: async () => {
    try {
      await fetch(`${BASE}/auth/logout`, { method: "POST", credentials: "include" });
    } finally {
      tokenStore.clear();
    }
  },
};
