/**
 * Cliente para POST /api/v1/metricas/archivos/upload (multipart, campo `archivo`).
 * Requiere NEXT_PUBLIC_DASHBOARD_API_URL (mismo host que métricas/reviews).
 */

import { fetchWithAuth } from "@/lib/fetch-with-auth";
import type { DashboardEnvelope } from "@/lib/reviews-api";
import { getDashboardApiBaseUrl } from "@/lib/reviews-api";

export type ArchivoUploadData = {
  blob_path: string;
  hash: string;
  nombre_archivo: string;
};

export async function uploadArchivo(
  file: File,
): Promise<DashboardEnvelope<ArchivoUploadData>> {
  const base = getDashboardApiBaseUrl();
  const url = `${base}/api/v1/metricas/archivos/upload`;
  const formData = new FormData();
  formData.append("archivo", file);

  try {
    const res = await fetchWithAuth(url, {
      method: "POST",
      body: formData,
    });

    let body: DashboardEnvelope<ArchivoUploadData>;
    try {
      body = (await res.json()) as DashboardEnvelope<ArchivoUploadData>;
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
