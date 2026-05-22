import { refreshAccessToken } from "@/lib/auth-api";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  updateAccessToken,
} from "@/lib/auth-storage";

// Deduplicates concurrent refresh calls — only one in-flight at a time.
let refreshPromise: Promise<string> | null = null;

let sessionExpiredHandler: (() => void) | null = null;

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  sessionExpiredHandler = handler;
}

/**
 * Decodes the JWT exp claim and returns true if the token is already
 * expired or will expire within the next 30 seconds.
 * Returns true on any parse error so we force a refresh on bad tokens.
 */
function isExpiredOrExpiringSoon(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const exp = payload.exp as number;
    return Date.now() / 1000 >= exp - 30;
  } catch {
    return true;
  }
}

/**
 * Triggers a token refresh, deduplicating concurrent calls.
 * Saves the new access token inside the promise chain so it is stored
 * exactly once regardless of how many callers are waiting.
 * On failure: signals the AuthProvider overlay and returns a promise that
 * never resolves, so no error propagates to components — the overlay and
 * redirect handle everything.
 */
function doRefresh(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    sessionExpiredHandler?.();
    clearTokens();
    return new Promise<string>(() => {});
  }

  if (!refreshPromise) {
    refreshPromise = refreshAccessToken(refreshToken)
      .then((newToken) => {
        updateAccessToken(newToken);
        refreshPromise = null;
        return newToken;
      })
      .catch((): Promise<string> => {
        sessionExpiredHandler?.();
        clearTokens();
        refreshPromise = null;
        return new Promise<string>(() => {});
      });
  }

  return refreshPromise;
}

async function getAccessTokenForFetch(): Promise<string | null> {
  if (typeof window !== "undefined") {
    return getAccessToken();
  }
  // Server-side: read from cookie set by auth-storage
  const { cookies } = await import("next/headers");
  const store = await cookies();
  return store.get("access_token")?.value ?? null;
}

export async function fetchWithAuth(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  let token = await getAccessTokenForFetch();

  // ── Proactive refresh ──────────────────────────────────────────────────────
  // Refresh before the request if the token is already expired or expires
  // within 30 s, avoiding an unnecessary 401 round-trip.
  if (token && typeof window !== "undefined" && isExpiredOrExpiringSoon(token)) {
    token = await doRefresh();
  }

  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res = await fetch(url, { ...options, headers });

  // ── Reactive refresh ───────────────────────────────────────────────────────
  // Handles 401s caused by clock skew or server-side token revocation even
  // when the local exp check passed.
  if (res.status === 401) {
    // Server-side: no refresh possible, return the 401 as-is.
    if (typeof window === "undefined") return res;

    const newToken = await doRefresh();

    const retryHeaders = new Headers(options.headers);
    retryHeaders.set("Authorization", `Bearer ${newToken}`);
    res = await fetch(url, { ...options, headers: retryHeaders });
  }

  return res;
}
