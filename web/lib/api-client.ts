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
