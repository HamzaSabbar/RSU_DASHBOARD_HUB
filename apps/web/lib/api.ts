import { auth } from "@/lib/auth";

const API_URL_INTERNAL =
  process.env.API_URL_INTERNAL ?? "http://api:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
  }
}

type FetchOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | null;
  searchParams?: Record<string, string | number | undefined>;
};

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const session = (await auth()) as (Record<string, unknown> | null);
  const accessToken = session?.accessToken as string | undefined;
  if (!accessToken) {
    throw new ApiError("unauthenticated", 401, null);
  }

  const url = new URL(path.replace(/^\//, ""), `${API_URL_INTERNAL}/`);
  if (options.searchParams) {
    for (const [k, v] of Object.entries(options.searchParams)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }

  const res = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(options.body && !(options.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(options.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      // ignore
    }
    throw new ApiError(`API ${res.status} on ${path}`, res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
