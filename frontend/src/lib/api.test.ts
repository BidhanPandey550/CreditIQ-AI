import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, tokenStore } from "./api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("secure API session handling", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    const storage: Storage = {
      get length() {
        return values.size;
      },
      clear: () => values.clear(),
      getItem: (key) => values.get(key) ?? null,
      key: (index) => [...values.keys()][index] ?? null,
      removeItem: (key) => values.delete(key),
      setItem: (key, value) => values.set(key, value),
    };
    Object.defineProperty(window, "localStorage", { configurable: true, value: storage });
    tokenStore.clear();
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rotates through the cookie endpoint and retries with an in-memory access token", async () => {
    tokenStore.set("expired-access");
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401))
      .mockResolvedValueOnce(jsonResponse({ access_token: "fresh-access" }))
      .mockResolvedValueOnce(jsonResponse({ id: "user-1" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.get<{ id: string }>("/auth/me")).resolves.toEqual({ id: "user-1" });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toContain("/auth/refresh");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: "POST",
      credentials: "include",
    });
    const retryHeaders = fetchMock.mock.calls[2][1]?.headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer fresh-access");
    expect(tokenStore.access).toBe("fresh-access");
    expect(window.localStorage.getItem("creditiq_access")).toBeNull();
    expect(window.localStorage.getItem("creditiq_refresh")).toBeNull();
  });

  it("deduplicates concurrent refresh attempts to protect rotation reuse detection", async () => {
    let resolveResponse: (response: Response) => void = () => undefined;
    const pending = new Promise<Response>((resolve) => {
      resolveResponse = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>().mockReturnValue(pending);
    vi.stubGlobal("fetch", fetchMock);

    const first = api.refreshSession();
    const second = api.refreshSession();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    resolveResponse(jsonResponse({ access_token: "rotated-access" }));
    await expect(Promise.all([first, second])).resolves.toEqual([true, true]);
    expect(tokenStore.access).toBe("rotated-access");
  });

  it("revokes the cookie session and clears memory on logout", async () => {
    tokenStore.set("active-access");
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await api.logout();

    expect(tokenStore.access).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/auth/logout"), {
      method: "POST",
      credentials: "include",
    });
  });
});
