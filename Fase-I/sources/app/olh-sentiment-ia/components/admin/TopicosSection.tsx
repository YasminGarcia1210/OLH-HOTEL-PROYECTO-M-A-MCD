"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  fetchTopicos,
  patchUmbralAlerta,
  type Topico,
} from "@/lib/topicos-admin-api";
import { recalcularSemestre } from "@/lib/metricas-admin-api";

function Portal({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;
  return createPortal(children, document.body);
}

function TipoBadge({ tipo }: { tipo: "clave" | "adicional" }) {
  return tipo === "clave" ? (
    <span className="tag tag-ok">Clave</span>
  ) : (
    <span
      className="tag"
      style={{ background: "rgba(167,139,250,0.1)", color: "#a78bfa" }}
    >
      Adicional
    </span>
  );
}

type ToastFn = (type: "success" | "error", message: string) => void;

function UmbralCell({
  topico,
  onSaved,
  onToast,
}: {
  topico: Topico;
  onSaved: (updated: Topico) => void;
  onToast?: ToastFn;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(topico.umbral_alerta));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  function handleCancel() {
    setValue(String(topico.umbral_alerta));
    setError(null);
    setEditing(false);
  }

  async function handleSave() {
    const parsed = parseInt(value, 10);
    if (isNaN(parsed) || parsed < 0 || parsed > 100) {
      setError("Valor entre 0 y 100");
      return;
    }
    if (parsed === topico.umbral_alerta) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError(null);
    const result = await patchUmbralAlerta(topico.id, parsed);
    setSaving(false);
    if (!result.ok || !result.data) {
      const msg = result.error?.mensaje ?? "Error al guardar";
      setError(msg);
      onToast?.("error", msg);
      return;
    }
    setEditing(false);
    onSaved(result.data);
    onToast?.("success", `Umbral de "${topico.nombre}" actualizado a ${parsed}%`);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") handleCancel();
  }

  if (!editing) {
    return (
      <div className="group flex items-center gap-2">
        <UmbralBar value={topico.umbral_alerta} />
        <span className="w-8 text-right tabular-nums text-on-surface/80">
          {topico.umbral_alerta}
        </span>
        <span className="text-on-surface/30 text-xs">%</span>
        <button
          type="button"
          title="Editar umbral"
          onClick={() => setEditing(true)}
          className="ml-1 flex h-6 w-6 items-center justify-center rounded opacity-0 transition-opacity group-hover:opacity-100 hover:bg-surface-container-high hover:text-gold-bright text-on-surface/40"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 14 }}>
            edit
          </span>
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="number"
          min={0}
          max={100}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={saving}
          className="w-20 rounded border border-gold-bright/40 bg-surface-container px-2 py-1 text-sm text-on-surface outline-none focus:ring-1 focus:ring-gold-bright/40 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          title="Guardar"
          className="flex h-7 w-7 items-center justify-center rounded bg-tertiary/20 text-tertiary transition-colors hover:bg-tertiary/30 disabled:opacity-40"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
            {saving ? "progress_activity" : "check"}
          </span>
        </button>
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          title="Cancelar"
          className="flex h-7 w-7 items-center justify-center rounded text-on-surface/40 transition-colors hover:bg-surface-container-high hover:text-on-surface disabled:opacity-40"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
            close
          </span>
        </button>
      </div>
      {error && (
        <span className="text-xs text-error">{error}</span>
      )}
    </div>
  );
}

function UmbralBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const color =
    pct >= 80 ? "#ff6b6b" : pct >= 60 ? "#ffaa5c" : "#3ddc97";
  return (
    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-container-highest">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

function RecalcularSemestreDialog({
  running,
  onConfirm,
  onCancel,
}: {
  running: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Portal>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
        onClick={(e) => !running && e.target === e.currentTarget && onCancel()}
      >
        <div className="w-full max-w-md rounded-[14px] bg-surface-container-high p-6 shadow-2xl">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gold-bright/10">
            <span className="material-symbols-outlined text-gold-bright">autorenew</span>
          </div>
          <h3 className="font-headline mb-2 text-lg font-bold text-on-background">
            Recalcular métricas del último semestre
          </h3>
          <p className="mb-3 text-sm text-on-surface/70">
            Esta operación recalculará las métricas de los últimos 6 meses naturales
            (incluyendo el mes actual) para el hotel seleccionado.
          </p>
          <p className="mb-6 text-sm text-on-surface/50">
            El proceso es secuencial y puede tardar varios minutos. Las métricas
            existentes serán sobrescritas con los nuevos cálculos.
          </p>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={running}
              className="font-label rounded px-4 py-2 text-xs uppercase tracking-widest text-on-surface/60 transition-colors hover:text-on-surface disabled:opacity-40"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={running}
              className="gradient-gold font-label text-on-primary flex items-center gap-2 rounded px-5 py-2 text-xs font-bold uppercase tracking-widest transition-opacity disabled:opacity-60"
            >
              {running && (
                <span
                  className="material-symbols-outlined animate-spin"
                  style={{ fontSize: 14 }}
                >
                  progress_activity
                </span>
              )}
              {running ? "Recalculando…" : "Recalcular"}
            </button>
          </div>
        </div>
      </div>
    </Portal>
  );
}

export function TopicosSection({
  hotelId,
  onToast,
}: {
  hotelId: number | null;
  onToast?: ToastFn;
}) {
  const [topicos, setTopicos] = useState<Topico[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [recalculando, setRecalculando] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchTopicos().then((res) => {
      setLoading(false);
      if (!res.ok || !res.data) {
        setError(res.error?.mensaje ?? "Error al cargar tópicos");
        return;
      }
      setTopicos(res.data);
    });
  }, []);

  function handleSaved(updated: Topico) {
    setTopicos((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
  }

  async function handleRecalcular() {
    if (hotelId == null || hotelId <= 0) {
      onToast?.("error", "No hay un hotel válido seleccionado para recalcular.");
      setConfirmOpen(false);
      return;
    }
    setRecalculando(true);
    const result = await recalcularSemestre(hotelId);
    setRecalculando(false);
    setConfirmOpen(false);

    if (!result.ok || !result.data) {
      onToast?.("error", result.error?.mensaje ?? "Error al recalcular el semestre");
      return;
    }

    const { exitos, fallos, periodos_solicitados } = result.data;
    if (fallos === 0) {
      onToast?.(
        "success",
        `Semestre recalculado correctamente (${exitos}/${periodos_solicitados} meses).`,
      );
    } else {
      onToast?.(
        "error",
        `Recálculo finalizado con fallos: ${exitos}/${periodos_solicitados} exitosos, ${fallos} fallidos.`,
      );
    }
  }

  const claves = topicos.filter((t) => t.tipo === "clave");
  const adicionales = topicos.filter((t) => t.tipo === "adicional");

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-headline text-xl font-bold text-on-background">
            Umbrales de alerta
          </h2>
          <p className="mt-1 text-sm text-on-surface/50">
            Porcentaje mínimo de score negativo para que un tópico active una alerta.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setConfirmOpen(true)}
          disabled={recalculando}
          title="Recalcular métricas del último semestre"
          className="gradient-gold font-label text-on-primary flex shrink-0 items-center gap-2 rounded-md px-5 py-2.5 text-[0.6875rem] font-bold uppercase tracking-widest transition-transform active:scale-95 disabled:opacity-60"
        >
          <span
            className={`material-symbols-outlined ${recalculando ? "animate-spin" : ""}`}
            style={{ fontSize: 16 }}
          >
            {recalculando ? "progress_activity" : "autorenew"}
          </span>
          {recalculando ? "Recalculando…" : "Recalcular semestre"}
        </button>
      </div>

      {confirmOpen && (
        <RecalcularSemestreDialog
          running={recalculando}
          onConfirm={handleRecalcular}
          onCancel={() => setConfirmOpen(false)}
        />
      )}

      <div className="rounded-[14px] bg-surface-container overflow-hidden">
        <div className="border-b border-surface-variant/20 px-6 py-4">
          <span className="font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
            Tópicos configurados
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-3 py-16 text-on-surface/40">
            <span className="material-symbols-outlined animate-spin" style={{ fontSize: 20 }}>
              progress_activity
            </span>
            <span className="text-sm">Cargando…</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <span className="material-symbols-outlined text-error" style={{ fontSize: 28 }}>
              error_outline
            </span>
            <p className="text-sm text-on-surface/60">{error}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-variant/20">
                  {["Tópico", "Slug", "Tipo", "Umbral de alerta"].map((h) => (
                    <th
                      key={h}
                      className="font-label px-6 py-3 text-left text-[0.625rem] uppercase tracking-widest text-on-surface/40"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...claves, ...adicionales].map((t, i) => (
                  <tr
                    key={t.id}
                    className={`border-b border-surface-variant/10 transition-colors hover:bg-surface-container-high ${
                      i % 2 === 0 ? "" : "bg-surface-container-low/30"
                    } ${!t.activo ? "opacity-40" : ""}`}
                  >
                    <td className="px-6 py-4 font-medium text-on-surface">
                      {t.nombre}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-on-surface/50">
                      {t.slug}
                    </td>
                    <td className="px-6 py-4">
                      <TipoBadge tipo={t.tipo} />
                    </td>
                    <td className="px-6 py-4">
                      <UmbralCell topico={t} onSaved={handleSaved} onToast={onToast} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
