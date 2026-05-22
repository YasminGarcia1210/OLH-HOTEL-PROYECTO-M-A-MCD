"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { logoutApi } from "@/lib/auth-api";
import {
  clearTokens,
  getAccessToken,
  getHotelIdFromToken,
  getRefreshToken,
  getRolFromToken,
} from "@/lib/auth-storage";
import { setSessionExpiredHandler } from "@/lib/fetch-with-auth";

type AuthContext = {
  username: string | null;
  rol: string | null;
  hotelId: number | null;
  logout: () => Promise<void>;
};

const AuthCtx = createContext<AuthContext>({
  username: null,
  rol: null,
  hotelId: null,
  logout: async () => {},
});

export function useAuth(): AuthContext {
  return useContext(AuthCtx);
}

function parseUsername(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return (payload.username as string) ?? null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [rol, setRol] = useState<string | null>(null);
  const [hotelId, setHotelId] = useState<number | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      setUsername(parseUsername(token));
      setRol(getRolFromToken(token));
      setHotelId(getHotelIdFromToken(token));
    }
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => setSessionExpired(true));
    return () => setSessionExpiredHandler(null);
  }, []);

  // Navigate only after React has rendered the overlay — prevents error flash.
  useEffect(() => {
    if (sessionExpired) {
      window.location.replace("/login");
    }
  }, [sessionExpired]);

  const logout = useCallback(async () => {
    const access = getAccessToken();
    const refresh = getRefreshToken();
    if (access && refresh) {
      await logoutApi(access, refresh).catch(() => {});
    }
    clearTokens();
    window.location.replace("/login");
  }, []);

  if (sessionExpired) {
    return (
      <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center gap-4 bg-surface-container">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-gold-bright border-t-transparent" />
        <p className="text-sm text-on-surface-variant">Cerrando sesión…</p>
      </div>
    );
  }

  return (
    <AuthCtx.Provider value={{ username, rol, hotelId, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}
