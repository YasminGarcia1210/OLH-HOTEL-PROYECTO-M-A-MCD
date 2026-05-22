const ACCESS_KEY = "auth_access_token";
const REFRESH_KEY = "auth_refresh_token";
const COOKIE_NAME = "access_token"; // leído por middleware

export function saveTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  setAccessCookie(access);
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function updateAccessToken(access: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  setAccessCookie(access);
}

export function getRolFromToken(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return (payload.rol as string) ?? null;
  } catch {
    return null;
  }
}

export function getHotelIdFromToken(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const hid = payload.hotel_id;
    return typeof hid === "number" ? hid : null;
  } catch {
    return null;
  }
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  document.cookie = `${COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax`;
}

function setAccessCookie(token: string): void {
  document.cookie = `${COOKIE_NAME}=${token}; path=/; SameSite=Lax`;
}
