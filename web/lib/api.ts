/** Minimal typed helper for calling the FastAPI backend with a Supabase JWT. */

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

export async function apiFetch<T>(
  path: string,
  token: string,
): Promise<ApiResult<T>> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    return { ok: false, error: "NEXT_PUBLIC_API_BASE_URL is not configured." };
  }

  try {
    const res = await fetch(`${base}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) {
      return { ok: false, error: `API responded with ${res.status}.` };
    }
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return {
      ok: false,
      error:
        "Could not reach the API. On the free tier it may be waking from sleep — try again in ~30s.",
    };
  }
}
