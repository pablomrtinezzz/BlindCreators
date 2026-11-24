export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Calls the backend through the authenticated Next.js proxy. Throws ApiError on non-2xx. */
export async function api<T>(path: string, init?: { method?: "GET" | "POST" | "DELETE"; body?: unknown }): Promise<T> {
  const res = await fetch(`/api/backend/${path.replace(/^\//, "")}`, {
    method: init?.method ?? "GET",
    headers: init?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const fetcher = <T,>(path: string) => api<T>(path);
