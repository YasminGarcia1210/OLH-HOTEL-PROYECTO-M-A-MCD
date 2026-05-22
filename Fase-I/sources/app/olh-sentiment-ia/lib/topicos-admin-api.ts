import { fetchWithAuth } from "@/lib/fetch-with-auth";
import { getDashboardApiBaseUrl } from "@/lib/reviews-api";
import type { DashboardEnvelope } from "@/lib/reviews-api";

export type Topico = {
  id: number;
  slug: string;
  nombre: string;
  tipo: "clave" | "adicional";
  umbral_alerta: number;
  activo: boolean;
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

export async function fetchTopicos(): Promise<DashboardEnvelope<Topico[]>> {
  try {
    const res = await fetchWithAuth(`${base()}/api/v1/topicos`);
    return safeJson<Topico[]>(res);
  } catch (e) {
    return netError(e);
  }
}

export async function patchUmbralAlerta(
  id: number,
  umbral_alerta: number,
): Promise<DashboardEnvelope<Topico>> {
  try {
    const res = await fetchWithAuth(`${base()}/api/v1/topicos/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ umbral_alerta }),
    });
    return safeJson<Topico>(res);
  } catch (e) {
    return netError(e);
  }
}
