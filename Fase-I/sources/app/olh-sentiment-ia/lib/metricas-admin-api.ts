import { fetchWithAuth } from "@/lib/fetch-with-auth";
import { getDashboardApiBaseUrl } from "@/lib/reviews-api";
import type { DashboardEnvelope } from "@/lib/reviews-api";

export type Periodo = {
  anio: number;
  mes: number;
};

export type RecalcularSemestreFalloItem = {
  anio: number;
  mes: number;
  http_status: number;
  codigo: string;
  mensaje?: string | null;
};

export type RecalcularSemestreResponse = {
  hotel_id: number;
  primer_periodo: Periodo;
  ultimo_periodo: Periodo;
  periodos_solicitados: number;
  exitos: number;
  fallos: number;
  fallidos: RecalcularSemestreFalloItem[];
  fecha_inicio: string;
  fecha_fin: string;
};

function base() {
  return getDashboardApiBaseUrl();
}

async function safeJson<T>(res: Response): Promise<DashboardEnvelope<T>> {
  try {
    const body = (await res.json()) as DashboardEnvelope<T>;
    if (!res.ok) {
      return {
        ok: false,
        data: null,
        error: body.error ?? { codigo: "HTTP_ERROR", mensaje: `HTTP ${res.status}` },
      };
    }
    return body;
  } catch {
    return {
      ok: false,
      data: null,
      error: { codigo: "RESPUESTA_INVALIDA", mensaje: `Respuesta no es JSON (HTTP ${res.status})` },
    };
  }
}

function netError<T>(e: unknown): DashboardEnvelope<T> {
  return {
    ok: false,
    data: null,
    error: { codigo: "RED", mensaje: e instanceof Error ? e.message : "Error de red" },
  };
}

export async function recalcularSemestre(
  hotel_id: number,
): Promise<DashboardEnvelope<RecalcularSemestreResponse>> {
  try {
    const res = await fetchWithAuth(`${base()}/api/v1/metricas/recalcular-semestre`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hotel_id }),
    });
    return safeJson<RecalcularSemestreResponse>(res);
  } catch (e) {
    return netError(e);
  }
}
