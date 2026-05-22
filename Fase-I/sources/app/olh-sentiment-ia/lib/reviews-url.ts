/**
 * URLs del explorador de reviews (filtros vía query string).
 */

export type ReviewsExplorerQuery = {
  page?: string;
  sentimiento?: string;
  topico_slug?: string;
  /** Rango efectivo (YYYY-MM-DD), siempre presente en enlaces para conservar el filtro. */
  fecha_desde: string;
  fecha_hasta: string;
};

export type ReviewsExplorerPatch = {
  page?: number | null;
  sentimiento?: "positivo" | "negativo" | "neutro" | null;
  topico_slug?: string | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
};

export function buildReviewsExplorerUrl(
  current: ReviewsExplorerQuery,
  patch: ReviewsExplorerPatch,
): string {
  const p = new URLSearchParams();

  const filterChanged =
    patch.sentimiento !== undefined ||
    patch.topico_slug !== undefined ||
    patch.fecha_desde !== undefined ||
    patch.fecha_hasta !== undefined;

  let pageNum: number;
  if (patch.page !== undefined) {
    pageNum = patch.page ?? 1;
  } else if (filterChanged) {
    pageNum = 1;
  } else {
    pageNum = Math.max(1, parseInt(current.page ?? "1", 10) || 1);
  }

  if (pageNum > 1) {
    p.set("page", String(pageNum));
  }

  let fecha_desde: string;
  if (patch.fecha_desde !== undefined) {
    fecha_desde = patch.fecha_desde ?? current.fecha_desde;
  } else {
    fecha_desde = current.fecha_desde;
  }
  let fecha_hasta: string;
  if (patch.fecha_hasta !== undefined) {
    fecha_hasta = patch.fecha_hasta ?? current.fecha_hasta;
  } else {
    fecha_hasta = current.fecha_hasta;
  }
  if (fecha_desde > fecha_hasta) {
    [fecha_desde, fecha_hasta] = [fecha_hasta, fecha_desde];
  }
  p.set("fecha_desde", fecha_desde);
  p.set("fecha_hasta", fecha_hasta);

  let sentimiento: string | undefined;
  if (patch.sentimiento !== undefined) {
    sentimiento = patch.sentimiento ?? undefined;
  } else {
    sentimiento = current.sentimiento;
  }
  if (
    sentimiento === "positivo" ||
    sentimiento === "negativo" ||
    sentimiento === "neutro"
  ) {
    p.set("sentimiento", sentimiento);
  }

  let topico_slug: string | undefined;
  if (patch.topico_slug !== undefined) {
    topico_slug = patch.topico_slug ?? undefined;
  } else {
    topico_slug = current.topico_slug;
  }
  if (topico_slug) {
    p.set("topico_slug", topico_slug);
  }

  const qs = p.toString();
  return qs ? `/dashboard/reviews?${qs}` : "/dashboard/reviews";
}
