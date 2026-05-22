"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/lib/auth-api";
import { saveTokens } from "@/lib/auth-storage";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await login(username.trim(), password);
      saveTokens(tokens.access_token, tokens.refresh_token);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">

      {/* Glow decorativo — gold */}
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full opacity-[0.07] blur-[120px]"
        style={{
          width: "600px",
          height: "600px",
          background:
            "radial-gradient(circle, #f2c35f 0%, #d4a847 50%, transparent 100%)",
        }}
      />

      <div className="relative z-10 w-full max-w-sm">

        {/* Marca */}
        <div className="mb-10 text-center">
          <span className="font-headline text-3xl font-bold italic text-gold-bright">
            Hoteles OLH
          </span>
          <p className="font-label mt-1 text-[0.6875rem] uppercase tracking-[0.15em] text-on-surface/40">
            Sentiment AI Intelligence
          </p>
        </div>

        {/* Card */}
        <div className="glass rounded-card border border-outline-variant/30 px-8 py-8">

          <h2 className="font-headline mb-6 text-base font-semibold text-on-surface">
            Iniciar sesión
          </h2>

          <form onSubmit={handleSubmit} className="space-y-5">

            {/* Usuario */}
            <div>
              <label className="font-label mb-2 block text-[0.6875rem] uppercase tracking-[0.1em] text-on-surface/50">
                Usuario
              </label>
              <div className="relative flex items-center">
                <span className="material-symbols-outlined pointer-events-none absolute left-3 text-[1.1rem] text-on-surface/30">
                  person
                </span>
                <input
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full rounded-lg border border-outline-variant/40 bg-surface-container-low py-2.5 pl-10 pr-4 text-sm text-on-surface placeholder-on-surface/25 outline-none transition focus:border-primary/60 focus:ring-1 focus:ring-primary/20"
                  placeholder="nombre de usuario"
                />
              </div>
            </div>

            {/* Contraseña */}
            <div>
              <label className="font-label mb-2 block text-[0.6875rem] uppercase tracking-[0.1em] text-on-surface/50">
                Contraseña
              </label>
              <div className="relative flex items-center">
                <span className="material-symbols-outlined pointer-events-none absolute left-3 text-[1.1rem] text-on-surface/30">
                  lock
                </span>
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-outline-variant/40 bg-surface-container-low py-2.5 pl-10 pr-10 text-sm text-on-surface placeholder-on-surface/25 outline-none transition focus:border-primary/60 focus:ring-1 focus:ring-primary/20"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 text-on-surface/30 transition hover:text-on-surface/60"
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  <span className="material-symbols-outlined text-[1.1rem]">
                    {showPassword ? "visibility_off" : "visibility"}
                  </span>
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-error/20 bg-error-container/10 px-3 py-2.5">
                <span className="material-symbols-outlined mt-0.5 text-[0.9rem] text-error">
                  error
                </span>
                <p className="font-label text-xs text-error">{error}</p>
              </div>
            )}

            {/* Botón */}
            <button
              type="submit"
              disabled={loading}
              className="gradient-gold font-label text-on-primary mt-2 flex w-full items-center justify-center gap-2 rounded-lg py-3 text-[0.6875rem] font-bold uppercase tracking-widest transition-transform active:scale-95 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-[1rem]">
                    progress_activity
                  </span>
                  Ingresando…
                </>
              ) : (
                "Ingresar"
              )}
            </button>
          </form>
        </div>

        {/* Pie */}
        <p className="font-label mt-6 text-center text-[0.625rem] uppercase tracking-[0.12em] text-on-surface/20">
          © {new Date().getFullYear()} Hoteles OLH
        </p>
      </div>
    </div>
  );
}
