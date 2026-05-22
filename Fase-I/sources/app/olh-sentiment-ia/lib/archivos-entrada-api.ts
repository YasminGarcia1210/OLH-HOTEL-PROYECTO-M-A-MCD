/**
 * GET /api/v1/metricas/archivos/entrada — blobs pendientes vs filas en log_archivos (paginado).
 */

import { fetchWithAuth } from "@/lib/fetch-with-auth";
import type { DashboardEnvelope, Paginacion } from "@/lib/reviews-api";
import { getDashboardApiBaseUrl } from "@/lib/reviews-api";

export type BlobPendiente = {
  blob_path: string;
  tamano_bytes: number;
  ultima_modificacion: string | null;
};

export type LogArchivoPipeline = {
  id: number;
  hotel_id: number;
  nombre_archivo_origen: string;
  drive_id_origen: string;
  hash: string;
  total_registros: number | null;
  registros_validos: number | null;
  registros_descartados: number | null;
  estado: string;
  etapa_error: string | null;
  mensaje_error: string | null;
  fecha_recepcion: string | null;
  fecha_limpieza: string | null;
  fecha_prediccion: string | null;
  fecha_topicos: string | null;
  fecha_metricas: string | null;
};

export type ArchivosEntradaData = {
  prefijo: string;
  pendientes: BlobPendiente[];
  en_pipeline: LogArchivoPipeline[];
  paginacion_pendientes: Paginacion;
  paginacion_pipeline: Paginacion;
  truncado?: boolean;
};

export type FetchArchivosEntradaParams = {
  limite?: number;
  pendientes_page?: number;
  pendientes_page_size?: number;
  pipeline_page?: number;
  pipeline_page_size?: number;
};

export async function fetchArchivosEntrada(
  params: FetchArchivosEntradaParams = {},
): Promise<DashboardEnvelope<ArchivosEntradaData>> {
  const base = getDashboardApiBaseUrl();
  const search = new URLSearchParams();
  if (params.limite != null) {
    search.set("limite", String(params.limite));
  }
  if (params.pendientes_page != null) {
    search.set("pendientes_page", String(params.pendientes_page));
  }
  if (params.pendientes_page_size != null) {
    search.set("pendientes_page_size", String(params.pendientes_page_size));
  }
  if (params.pipeline_page != null) {
    search.set("pipeline_page", String(params.pipeline_page));
  }
  if (params.pipeline_page_size != null) {
    search.set("pipeline_page_size", String(params.pipeline_page_size));
  }
  const q = search.toString();
  const url = `${base}/api/v1/metricas/archivos/entrada${q ? `?${q}` : ""}`;

  try {
    const res = await fetchWithAuth(url, { method: "GET", cache: "no-store" });
    let body: DashboardEnvelope<ArchivosEntradaData>;
    try {
      body = (await res.json()) as DashboardEnvelope<ArchivosEntradaData>;
    } catch {
      return {
        ok: false,
        data: null,
        error: {
          codigo: "RESPUESTA_INVALIDA",
          mensaje: `La respuesta no es JSON válido (HTTP ${res.status}).`,
        },
      };
    }
    if (!res.ok) {
      return {
        ok: false,
        data: null,
        error:
          body.error ?? {
            codigo: "HTTP_ERROR",
            mensaje: `HTTP ${res.status}`,
          },
      };
    }
    return body;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Error de red";
    return {
      ok: false,
      data: null,
      error: { codigo: "RED", mensaje: msg },
    };
  }
}
