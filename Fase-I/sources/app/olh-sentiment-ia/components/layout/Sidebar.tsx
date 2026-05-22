"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  fetchArchivosEntrada,
  type BlobPendiente,
} from "@/lib/archivos-entrada-api";
import { basename } from "@/lib/path-utils";
import { getReviewsExplorerHotelId } from "@/lib/reviews-api";

const ALL_NAV = [
  { href: "/dashboard", label: "DASHBOARD", icon: "dashboard", roles: null },
  { href: "/dashboard/reviews", label: "REVIEWS", icon: "manage_search", roles: null },
  { href: "/upload", label: "UPLOAD", icon: "cloud_upload", roles: null },
  { href: "/admin", label: "SETTINGS", icon: "settings", roles: ["admin"] },
] as const;

const ANALYSIS_LAUNCHED_KEY = "olh_analysis_webhook_blob_paths_v1";
const PENDIENTES_PAGE_SIZE = 100;

const PLATAFORMAS = [
  { value: "booking", label: "Booking" },
  { value: "tripadvisor", label: "TripAdvisor" },
  { value: "google", label: "Google" },
  { value: "otro", label: "Otro" },
] as const;

const inputCls =
  "w-full rounded border border-surface-variant/40 bg-surface-container px-3 py-2 text-sm text-on-surface outline-none transition focus:border-gold-bright/60 focus:ring-1 focus:ring-gold-bright/30";

function readLaunchedBlobPaths(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = sessionStorage.getItem(ANALYSIS_LAUNCHED_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as unknown;
    if (!Array.isArray(arr)) return new Set();
    return new Set(arr.filter((x): x is string => typeof x === "string"));
  } catch {
    return new Set();
  }
}

function appendLaunchedBlobPath(blobPath: string): void {
  const next = readLaunchedBlobPaths();
  next.add(blobPath);
  sessionStorage.setItem(ANALYSIS_LAUNCHED_KEY, JSON.stringify([...next]));
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const u = ["KB", "MB", "GB"];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < u.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${u[i]}`;
}

function Portal({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    queueMicrotask(() => setMounted(true));
  }, []);
  if (!mounted) return null;
  return createPortal(children, document.body);
}

function NewAnalysisModal({
  hotelId,
  onSuccess,
  onCancel,
}: {
  hotelId: number | null;
  onSuccess: () => void;
  onCancel: () => void;
}) {
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [pendientes, setPendientes] = useState<BlobPendiente[]>([]);
  const [selectedBlobPath, setSelectedBlobPath] = useState("");
  const [plataforma, setPlataforma] =
    useState<(typeof PLATAFORMAS)[number]["value"]>("booking");
  const [submitting, setSubmitting] = useState(false);
  const [webhookError, setWebhookError] = useState<string | null>(null);

  const webhookUrl = process.env.NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL ?? "";

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setFetchError(null);
      const res = await fetchArchivosEntrada({
        pendientes_page: 1,
        pendientes_page_size: PENDIENTES_PAGE_SIZE,
        pipeline_page: 1,
        pipeline_page_size: 1,
      });
      if (cancelled) return;
      setLoading(false);
      if (!res.ok || !res.data) {
        setFetchError(
          res.error?.mensaje ?? "No se pudo cargar los archivos pendientes.",
        );
        setPendientes([]);
        setSelectedBlobPath("");
        return;
      }
      const list = res.data.pendientes;
      setPendientes(list);
      const launched = readLaunchedBlobPaths();
      const available = list.filter((p) => !launched.has(p.blob_path));
      setSelectedBlobPath(available[0]?.blob_path ?? "");
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit() {
    if (!webhookUrl || !selectedBlobPath || submitting) return;
    if (readLaunchedBlobPaths().has(selectedBlobPath)) {
      setWebhookError(
        "Este archivo ya fue enviado a análisis en esta sesión del navegador.",
      );
      return;
    }
    setWebhookError(null);
    setSubmitting(true);
    const hid = hotelId ?? getReviewsExplorerHotelId();
    const nombreArchivo = basename(selectedBlobPath);
    try {
      const res = await fetch(webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hotel_id: hid,
          drive_id_origen: selectedBlobPath,
          nombre_archivo_origen: nombreArchivo,
          plataforma,
        }),
      });
      if (!res.ok) {
        setWebhookError(`El webhook respondió con error (HTTP ${res.status}).`);
        setSubmitting(false);
        return;
      }
      appendLaunchedBlobPath(selectedBlobPath);
      onSuccess();
    } catch {
      setWebhookError(
        "No se pudo contactar el webhook. Revisa la red e inténtalo de nuevo.",
      );
      setSubmitting(false);
    }
  }

  const launched = readLaunchedBlobPaths();
  const hasSelectable = pendientes.some((p) => !launched.has(p.blob_path));
  const canSubmit =
    Boolean(webhookUrl) &&
    !loading &&
    !fetchError &&
    Boolean(selectedBlobPath) &&
    hasSelectable &&
    !submitting;

  return (
    <Portal>
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm"
        onClick={(e) => {
          if (e.target === e.currentTarget && !submitting) onCancel();
        }}
      >
        <div className="w-full max-w-md rounded-[14px] bg-surface-container-high p-6 shadow-2xl">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gold-bright/10">
            <span
              className="material-symbols-outlined text-gold-bright"
              style={{
                fontVariationSettings:
                  "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24",
              }}
            >
              auto_awesome
            </span>
          </div>

          <h3 className="font-headline mb-2 text-lg font-bold text-on-background">
            Iniciar nuevo análisis
          </h3>
          <p className="mb-4 text-sm text-on-surface/60">
            Elige un archivo pendiente de procesar y la plataforma de origen de
            las reseñas. La operación puede tardar varios minutos; te
            notificaremos por correo cuando esté lista.
          </p>

          {!webhookUrl ? (
            <p className="mb-4 text-sm text-error" role="alert">
              Falta configurar{" "}
              <span className="font-mono text-xs">NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL</span>
              .
            </p>
          ) : null}

          {fetchError ? (
            <p className="mb-4 text-sm text-error" role="alert">
              {fetchError}
            </p>
          ) : null}

          {webhookError ? (
            <p className="mb-4 text-sm text-error" role="alert">
              {webhookError}
            </p>
          ) : null}

          <div className="mb-4 space-y-4">
            <div>
              <label
                htmlFor="analysis-pendiente"
                className="font-label mb-1.5 block text-[0.6875rem] uppercase tracking-widest text-on-surface/40"
              >
                Archivo pendiente
              </label>
              {loading ? (
                <p className="text-sm text-on-surface/45">Cargando…</p>
              ) : pendientes.length === 0 ? (
                <p className="text-sm text-on-surface/45">
                  No hay archivos pendientes de procesar.
                </p>
              ) : (
                <select
                  id="analysis-pendiente"
                  className={inputCls}
                  disabled={submitting || !hasSelectable}
                  value={
                    hasSelectable &&
                    pendientes.some((p) => p.blob_path === selectedBlobPath)
                      ? selectedBlobPath
                      : ""
                  }
                  onChange={(e) => setSelectedBlobPath(e.target.value)}
                >
                  {!hasSelectable ? (
                    <option value="">Todos los archivos ya fueron enviados</option>
                  ) : null}
                  {pendientes.map((p) => {
                    const sent = launched.has(p.blob_path);
                    const label = `${basename(p.blob_path)} · ${formatBytes(p.tamano_bytes)}`;
                    return (
                      <option
                        key={p.blob_path}
                        value={p.blob_path}
                        disabled={sent}
                        title={
                          sent
                            ? "Ya iniciado en esta sesión del navegador"
                            : undefined
                        }
                      >
                        {label}
                        {sent ? " (ya enviado)" : ""}
                      </option>
                    );
                  })}
                </select>
              )}
            </div>

            <div>
              <label
                htmlFor="analysis-plataforma"
                className="font-label mb-1.5 block text-[0.6875rem] uppercase tracking-widest text-on-surface/40"
              >
                Plataforma
              </label>
              <select
                id="analysis-plataforma"
                className={inputCls}
                disabled={submitting}
                value={plataforma}
                onChange={(e) =>
                  setPlataforma(
                    e.target.value as (typeof PLATAFORMAS)[number]["value"],
                  )
                }
              >
                {PLATAFORMAS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              disabled={submitting}
              onClick={onCancel}
              className="font-label rounded px-4 py-2 text-xs uppercase tracking-widest text-on-surface/60 transition-colors hover:text-on-surface disabled:opacity-40"
            >
              Cancelar
            </button>
            <button
              type="button"
              disabled={!canSubmit}
              onClick={() => void handleSubmit()}
              className="gradient-gold font-label text-on-primary flex items-center gap-2 rounded px-5 py-2 text-xs font-bold uppercase tracking-widest transition-opacity enabled:hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 14 }}
              >
                play_arrow
              </span>
              {submitting ? "Enviando…" : "Iniciar"}
            </button>
          </div>
        </div>
      </div>
    </Portal>
  );
}

function AnalysisToast({ onDismiss }: { onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 6000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <Portal>
      <div
        className="fixed bottom-6 right-6 z-[70] flex max-w-sm items-start gap-3 rounded-lg border border-tertiary/30 bg-surface-container-high px-4 py-3 shadow-xl"
        style={{ pointerEvents: "auto" }}
      >
        <span
          className="material-symbols-outlined mt-0.5 shrink-0 text-tertiary"
          style={{ fontSize: 18 }}
        >
          check_circle
        </span>
        <div className="flex-1">
          <p className="text-sm font-medium text-on-surface">
            ¡Procesamiento iniciado!
          </p>
          <p className="mt-0.5 text-xs text-on-surface/60">
            Te avisaremos por correo cuando las reseñas estén listas.
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 text-on-surface/40 transition-colors hover:text-on-surface"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
            close
          </span>
        </button>
      </div>
    </Portal>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { logout, rol, hotelId } = useAuth();
  const [showConfirm, setShowConfirm] = useState(false);
  const [showToast, setShowToast] = useState(false);

  const nav = ALL_NAV.filter(
    (item) => item.roles === null || item.roles.includes(rol as "admin"),
  );

  return (
    <>
      <aside className="border-surface-variant/10 fixed left-0 top-0 z-50 hidden h-screen w-64 flex-col border-r bg-surface-container-lowest md:flex">
        <div className="p-8">
          <h1 className="font-headline text-lg text-gold-bright">Sentiment AI</h1>
          <p className="font-label text-[0.6875rem] uppercase tracking-[0.1em] text-on-surface/40">
            Intelligence Suite
          </p>
        </div>
        <nav className="mt-4 flex-1">
          {nav.map((item) => {
            const active =
              item.label === "DASHBOARD"
                ? pathname === "/dashboard" || pathname === "/"
                : item.label === "REVIEWS"
                  ? pathname === "/dashboard/reviews"
                  : pathname === item.href ||
                    (item.href === "/admin" && pathname?.startsWith("/admin"));
            return (
              <Link
                key={`${item.href}-${item.label}`}
                href={item.href}
                className={`group flex items-center gap-4 px-6 py-4 transition-all ${
                  active
                    ? "border-gold-bright bg-surface-container text-gold-bright border-r-2"
                    : "text-on-surface/40 hover:bg-surface hover:text-on-surface"
                }`}
              >
                <span
                  className="material-symbols-outlined"
                  style={
                    active
                      ? {
                          fontVariationSettings:
                            "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24",
                        }
                      : undefined
                  }
                >
                  {item.icon}
                </span>
                <span className="font-label text-[0.6875rem] uppercase tracking-[0.1em]">
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
        <div className="p-6">
          <button
            type="button"
            onClick={() => setShowConfirm(true)}
            className="font-label text-on-primary gradient-gold mb-8 w-full cursor-pointer rounded-md py-3 text-[0.6875rem] font-bold uppercase tracking-widest transition-transform active:scale-95"
          >
            New Analysis
          </button>
          <div className="flex flex-col gap-2">
            <button
              className="text-on-surface/40 hover:text-error flex cursor-pointer items-center gap-4 px-6 py-2 transition-colors"
              type="button"
              onClick={logout}
            >
              <span className="material-symbols-outlined text-sm">logout</span>
              <span className="font-label text-[0.6875rem] uppercase tracking-[0.1em]">
                Logout
              </span>
            </button>
          </div>
        </div>
      </aside>

      {showConfirm && (
        <NewAnalysisModal
          hotelId={hotelId}
          onSuccess={() => {
            setShowConfirm(false);
            setShowToast(true);
          }}
          onCancel={() => setShowConfirm(false)}
        />
      )}

      {showToast && <AnalysisToast onDismiss={() => setShowToast(false)} />}
    </>
  );
}