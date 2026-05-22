"use client";

import { useEffect, useState } from "react";

import { SectionDivider } from "@/components/dashboard/SectionDivider";
import type { Paginacion } from "@/lib/reviews-api";
import {
  type ArchivosEntradaData,
  type BlobPendiente,
  type LogArchivoPipeline,
  fetchArchivosEntrada,
} from "@/lib/archivos-entrada-api";
import { basename } from "@/lib/path-utils";

const PAGE_SIZE = 20;

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

function formatFecha(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("es", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function EntradaPagination({
  paginacion,
  onPageChange,
  loading,
}: {
  paginacion: Paginacion;
  onPageChange: (page: number) => void;
  loading: boolean;
}) {
  const { page, total_pages, total } = paginacion;
  if (total === 0) {
    return (
      <div className="px-8 py-4 font-label text-xs uppercase tracking-widest text-on-surface/35">
        Sin registros
      </div>
    );
  }
  const canPrev = page > 1 && !loading;
  const canNext = page < total_pages && !loading;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-8 py-4">
      <p className="text-sm text-on-surface/50">
        Página {page} de {Math.max(1, total_pages)} · {total} en total
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={!canPrev}
          onClick={() => onPageChange(page - 1)}
          className="font-label rounded-lg px-3 py-1.5 text-xs uppercase tracking-widest text-on-surface transition-colors duration-300 ease-in-out enabled:hover:bg-surface-container-high enabled:hover:text-primary disabled:opacity-30"
        >
          Anterior
        </button>
        <button
          type="button"
          disabled={!canNext}
          onClick={() => onPageChange(page + 1)}
          className="font-label rounded-lg px-3 py-1.5 text-xs uppercase tracking-widest text-on-surface transition-colors duration-300 ease-in-out enabled:hover:bg-surface-container-high enabled:hover:text-primary disabled:opacity-30"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}

function EstadoPipelineBadge({ estado }: { estado: string }) {
  const e = estado.toLowerCase();
  const hecho = new Set([
    "cleaned",
    "topics_identified",
    "completed",
    "topicado",
  ]);
  if (e === "error" || e.endsWith("_error")) {
    return (
      <span className="rounded-full bg-error-container/80 px-3 py-1 font-label text-[0.6rem] font-bold uppercase tracking-widest text-on-error-container">
        {estado}
      </span>
    );
  }
  if (hecho.has(e)) {
    return (
      <span className="rounded-full bg-tertiary-container/50 px-3 py-1 font-label text-[0.6rem] font-bold uppercase tracking-widest text-on-tertiary-fixed-variant">
        {estado}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 font-label text-[0.6rem] font-bold uppercase tracking-widest text-primary">
      <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
      {estado}
    </span>
  );
}

function TablaPendientes({
  rows,
  loading,
}: {
  rows: BlobPendiente[];
  loading: boolean;
}) {
  return (
    <div className="overflow-hidden rounded-xl bg-surface-container shadow-glow">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="bg-surface-container-high/50">
            <th className="px-8 py-4 font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
              Archivo
            </th>
            <th className="px-8 py-4 font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
              Tamaño
            </th>
            <th className="px-8 py-4 font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
              Última modificación
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/5">
          {loading ? (
            <tr>
              <td
                colSpan={3}
                className="px-8 py-8 text-sm text-on-surface/45"
              >
                Cargando…
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td
                colSpan={3}
                className="px-8 py-8 text-sm text-on-surface/45"
              >
                No hay blobs pendientes de lectura.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={row.blob_path}
                className="transition-colors hover:bg-surface-container-high/30"
              >
                <td className="px-8 py-5">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-on-surface/25">
                      cloud_queue
                    </span>
                    <span
                      className="max-w-[min(100%,28rem)] truncate font-semibold"
                      title={row.blob_path}
                    >
                      {basename(row.blob_path)}
                    </span>
                  </div>
                </td>
                <td className="px-8 py-5 text-sm text-on-surface/60">
                  {formatBytes(row.tamano_bytes)}
                </td>
                <td className="px-8 py-5 text-sm text-on-surface/60">
                  {formatFecha(row.ultima_modificacion)}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function TablaPipeline({
  rows,
  loading,
}: {
  rows: LogArchivoPipeline[];
  loading: boolean;
}) {
  return (
    <div className="overflow-hidden rounded-xl bg-surface-container shadow-glow">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="bg-surface-container-high/50">
            <th className="px-8 py-4 font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
              Archivo
            </th>
            <th className="px-8 py-4 font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
              Recepción
            </th>
            <th className="px-8 py-4 font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
              Estado
            </th>
            <th className="px-8 py-4 font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
              Registros
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/5">
          {loading ? (
            <tr>
              <td
                colSpan={4}
                className="px-8 py-8 text-sm text-on-surface/45"
              >
                Cargando…
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td
                colSpan={4}
                className="px-8 py-8 text-sm text-on-surface/45"
              >
                No hay archivos registrados en el pipeline.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={row.id}
                className="transition-colors hover:bg-surface-container-high/30"
              >
                <td className="px-8 py-5">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-on-surface/25">
                        description
                      </span>
                      <span
                        className="max-w-[min(100%,24rem)] truncate font-semibold"
                        title={row.nombre_archivo_origen}
                      >
                        {row.nombre_archivo_origen}
                      </span>
                    </div>
                    {row.mensaje_error ? (
                      <span
                        className="max-w-xl truncate pl-8 text-xs text-error/90"
                        title={row.mensaje_error}
                      >
                        {row.mensaje_error}
                      </span>
                    ) : null}
                  </div>
                </td>
                <td className="px-8 py-5 text-sm text-on-surface/60">
                  {formatFecha(row.fecha_recepcion)}
                </td>
                <td className="px-8 py-5">
                  <EstadoPipelineBadge estado={row.estado} />
                </td>
                <td className="px-8 py-5 text-sm text-on-surface/70">
                  {row.registros_validos != null && row.total_registros != null
                    ? `${row.registros_validos} / ${row.total_registros}`
                    : row.total_registros != null
                      ? String(row.total_registros)
                      : "—"}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function ArchivosEntradaPanels() {
  const [pendPage, setPendPage] = useState(1);
  const [pipePage, setPipePage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ArchivosEntradaData | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError(null);
      const res = await fetchArchivosEntrada({
        pendientes_page: pendPage,
        pendientes_page_size: PAGE_SIZE,
        pipeline_page: pipePage,
        pipeline_page_size: PAGE_SIZE,
      });
      if (cancelled) return;
      setLoading(false);
      if (!res.ok || !res.data) {
        setError(res.error?.mensaje ?? "No se pudo cargar el listado.");
        setData(null);
        return;
      }
      setData(res.data);
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [pendPage, pipePage]);

  const pendientes = data?.pendientes ?? [];
  const pipeline = data?.en_pipeline ?? [];
  const pagPend = data?.paginacion_pendientes;
  const pagPipe = data?.paginacion_pipeline;

  return (
    <div className="space-y-14">
      {error !== null ? (
        <div
          className="bg-error/10 text-error border-error/20 rounded-card border px-4 py-3 text-sm"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      <section className="space-y-4">
        <SectionDivider label="Sin procesar (pendientes)" />
        <p className="max-w-3xl text-sm text-on-surface/55">
          Blobs en el prefijo{" "}
          <span className="font-mono text-on-surface/70">
            {data?.prefijo ?? "…"}
          </span>{" "}
          que aún no están vinculados al pipeline en base de datos.
          {data?.truncado ? (
            <span className="ml-1 text-primary">
              Listado de blobs truncado (límite Azure alcanzado).
            </span>
          ) : null}
        </p>
        <TablaPendientes rows={pendientes} loading={loading} />
        {pagPend ? (
          <EntradaPagination
            paginacion={pagPend}
            loading={loading}
            onPageChange={setPendPage}
          />
        ) : null}
      </section>

      <section className="space-y-4">
        <SectionDivider label="Archivos procesados (pipeline)" />
        <p className="max-w-3xl text-sm text-on-surface/55">
          Registros en{" "}
          <span className="font-mono text-on-surface/70">log_archivos</span>:
          limpieza, predicción, tópicos y métricas según el estado actual.
        </p>
        <TablaPipeline rows={pipeline} loading={loading} />
        {pagPipe ? (
          <EntradaPagination
            paginacion={pagPipe}
            loading={loading}
            onPageChange={setPipePage}
          />
        ) : null}
      </section>
    </div>
  );
}
