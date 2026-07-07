import { createClient } from "@/lib/supabase/client";

/**
 * Call the FastAPI backend from the browser with the current Supabase JWT.
 * Returns the raw Response so callers can branch on status.
 */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token;

  return fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

/**
 * Fetch JSON from the backend, throwing on a non-2xx response so it plugs
 * straight into React Query's `queryFn`. Use `apiFetch` when you need the raw
 * Response (e.g. to branch on status).
 */
export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await apiFetch(path, init);
  } catch {
    throw new Error(
      "Couldn't reach the API. On the free tier it may be waking from sleep — try again in ~30s.",
    );
  }
  if (!res.ok) throw new Error(`API responded with ${res.status}.`);
  return (await res.json()) as T;
}
