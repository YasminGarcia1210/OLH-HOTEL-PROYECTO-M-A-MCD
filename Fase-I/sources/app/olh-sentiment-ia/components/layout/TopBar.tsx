"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";

export function TopBar() {
  const { username, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  async function handleLogout() {
    setLoggingOut(true);
    await logout();
  }

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const initial = username ? username[0].toUpperCase() : "?";

  return (
    <header className="border-surface-variant/20 sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b bg-surface px-8 shadow-[0px_12px_32px_rgba(225,226,237,0.04)]">
      <div className="flex items-center gap-8">
        <span className="font-headline text-gold-bright text-xl font-bold italic">
          Hoteles OLH
        </span>
      </div>
      <div className="flex items-center gap-6">
        {/* Avatar + dropdown */}
        <div ref={ref} className="relative">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label="Perfil de usuario"
            aria-expanded={open}
            className="flex size-8 items-center justify-center rounded-full border border-primary/20 bg-surface-container font-bold text-xs text-gold-bright transition-colors hover:border-primary/50 focus:outline-none"
          >
            {initial}
          </button>

          {open && (
            <div className="glass absolute right-0 top-11 z-50 w-52 rounded-lg border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-lg">
              <div className="mb-3 flex items-center gap-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-surface-container font-bold text-sm text-gold-bright">
                  {initial}
                </div>
                <div className="min-w-0">
                  <p className="font-label truncate text-[0.6875rem] uppercase tracking-[0.1em] text-on-surface">
                    {username ?? "—"}
                  </p>
                  <p className="font-label text-[0.6rem] uppercase tracking-[0.08em] text-on-surface/40">
                    Usuario
                  </p>
                </div>
              </div>

              <div className="mb-3 h-px bg-outline-variant/20" />

              <button
                type="button"
                onClick={handleLogout}
                disabled={loggingOut}
                className="flex w-full cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-on-surface/50 transition-all hover:bg-error/5 hover:text-error disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span
                  className={`material-symbols-outlined text-sm ${loggingOut ? "animate-spin" : ""}`}
                >
                  {loggingOut ? "progress_activity" : "logout"}
                </span>
                <span className="font-label text-[0.6875rem] uppercase tracking-[0.1em]">
                  {loggingOut ? "Cerrando…" : "Cerrar sesión"}
                </span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
