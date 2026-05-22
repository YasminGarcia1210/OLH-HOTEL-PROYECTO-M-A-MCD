/**
 * Cliente HTTP para GET /api/v1/metricas/reviews (contrato OpenAPI).
 * Pensado para ejecutarse en el servidor (Route Handlers / Server Components).
 */

export type DashboardEnvelope<T> = {
  ok: boolean;
  data: T | null;
  error: { codigo: string; mensaje: string } | null;
};

export type Paginacion = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type SentimientoPrediccion = {
  sentimiento: "positivo" | "negativo" | "neutro";
  confianza: number | null;
  modelo_version?: string | null;
};

export type TopicoAsignado = {
  topico_id: number;
  slug: string;
  nombre: string;
  score_topico: number | null;
  sentimiento: "positivo" | "negativo" | "neutro" | null;
  fragmento: string | null;
};

export type ReviewListItem = {
  review_id: number;
  hotel_id: number;
  fecha_review: string;
  texto_limpio: string;
  plataforma: string | null;
  idioma: string | null;
  titulo: string | null;
  prediccion: SentimientoPrediccion;
  topicos: TopicoAsignado[];
};

export type ReviewsListResponse = {
  items: ReviewListItem[];
  paginacion: Paginacion;
};

export type FetchDashboardReviewsParams = {
  hotel_id: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  sentimiento?: "positivo" | "negativo" | "neutro";
  topico_slug?: string;
  topico_id?: number;
  page?: number;
  page_size?: number;
  orden?: "fecha_desc" | "fecha_asc";
};

import { fetchWithAuth } from "@/lib/fetch-with-auth";

export function getDashboardApiBaseUrl(): string {
  const raw =
    process.env.NEXT_PUBLIC_DASHBOARD_API_URL ?? "http://127.0.0.1:5002";
  return raw.replace(/\/$/, "");
}

function getDefaultHotelId(): number {
  const n = Number(process.env.NEXT_PUBLIC_DASHBOARD_HOTEL_ID ?? "1");
  return Number.isFinite(n) && n > 0 ? n : 1;
}

export function getReviewsExplorerHotelId(): number {
  return getDefaultHotelId();
}

export async function fetchDashboardReviews(
  params: FetchDashboardReviewsParams,
): Promise<DashboardEnvelope<ReviewsListResponse>> {
  const base = getDashboardApiBaseUrl();
  const q = new URLSearchParams();
  q.set("hotel_id", String(params.hotel_id));
  if (params.fecha_desde) q.set("fecha_desde", params.fecha_desde);
  if (params.fecha_hasta) q.set("fecha_hasta", params.fecha_hasta);
  if (params.sentimiento) q.set("sentimiento", params.sentimiento);
  if (params.topico_slug) q.set("topico_slug", params.topico_slug);
  if (params.topico_id != null) q.set("topico_id", String(params.topico_id));
  if (params.page != null) q.set("page", String(params.page));
  if (params.page_size != null) q.set("page_size", String(params.page_size));
  if (params.orden) q.set("orden", params.orden);

  const url = `${base}/api/v1/metricas/reviews?${q.toString()}`;
  try {
    const res = await fetchWithAuth(url, { cache: "no-store" });
    let body: DashboardEnvelope<ReviewsListResponse>;
    try {
      body = (await res.json()) as DashboardEnvelope<ReviewsListResponse>;
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
