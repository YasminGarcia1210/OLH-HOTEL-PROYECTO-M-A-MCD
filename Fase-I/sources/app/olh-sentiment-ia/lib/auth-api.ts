import { getDashboardApiBaseUrl } from "@/lib/reviews-api";

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
};

export async function login(
  username: string,
  password: string,
): Promise<AuthTokens> {
  const base = getDashboardApiBaseUrl();
  const res = await fetch(`${base}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const body = await res.json();
  if (!res.ok || !body.ok) {
    throw new Error(body.error?.mensaje ?? "Error al iniciar sesión");
  }
  return body.data as AuthTokens;
}

export async function refreshAccessToken(
  refreshToken: string,
): Promise<string> {
  const base = getDashboardApiBaseUrl();
  const res = await fetch(`${base}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { Authorization: `Bearer ${refreshToken}` },
  });

  const body = await res.json();
  if (!res.ok || !body.ok) throw new Error("Sesión expirada");
  return body.data.access_token as string;
}

export async function logoutApi(
  accessToken: string,
  refreshToken: string,
): Promise<void> {
  const base = getDashboardApiBaseUrl();
  await fetch(`${base}/api/v1/auth/logout`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}
