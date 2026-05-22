import { fetchWithAuth } from "@/lib/fetch-with-auth";
import { getDashboardApiBaseUrl } from "@/lib/reviews-api";
import type { DashboardEnvelope } from "@/lib/reviews-api";

export type Hotel = {
  id: number;
  nombre: string;
  ciudad: string | null;
  pais: string | null;
};

export async function fetchHoteles(): Promise<DashboardEnvelope<Hotel[]>> {
  try {
    const res = await fetchWithAuth(`${getDashboardApiBaseUrl()}/api/v1/hoteles`);
    const body = (await res.json()) as DashboardEnvelope<Hotel[]>;
    if (!res.ok) {
      return {
        ok: false,
        data: null,
        error: body.error ?? { codigo: "HTTP_ERROR", mensaje: `HTTP ${res.status}` },
      };
    }
    return body;
  } catch (e) {
    return {
      ok: false,
      data: null,
      error: { codigo: "RED", mensaje: e instanceof Error ? e.message : "Error de red" },
    };
  }
}
