/**
 * Cliente HTTP para KPIs y tópicos del dashboard (DashboardBackend).
 */

import type { DashboardPeriod, YearMonth } from "@/lib/dashboard-period";
import { getHeroMonthWindow } from "@/lib/dashboard-period";
import { fetchWithAuth } from "@/lib/fetch-with-auth";
import type {
  CategoryScore,
  DataStrength,
  ExecutiveKpi,
  HeroKpis,
  InsightRank,
  PainPointCard,
  RiskAlerts,
  TrendSeries,
} from "@/lib/mock-data";
import {
  type DashboardEnvelope,
  fetchDashboardReviews,
  getDashboardApiBaseUrl,
} from "@/lib/reviews-api";

export type MetricasKpisData = {
  sentimiento_promedio: {
    score: number;
    cambio_pct: number;
    tendencia: string;
  };
  reviews_analizadas: number;
  topicos_con_alerta: number;
};

/** Respuesta equivalente a “sin fila en BD” (API ok pero sin datos). */
const KPIS_SIN_FILA: MetricasKpisData = {
  sentimiento_promedio: {
    score: 0,
    cambio_pct: 0,
    tendencia: "stable",
  },
  reviews_analizadas: 0,
  topicos_con_alerta: 0,
};

function kpiTieneDatosMensuales(k: MetricasKpisData): boolean {
  return k.reviews_analizadas > 0;
}

export type MetricasTopicoRow = {
  topico_id: number;
  slug: string;
  nombre: string;
  tipo: string;
  score_promedio: number;
  cambio_pct_vs_anterior: number;
  total_menciones: number;
  alerta: boolean;
  tendencia: string;
};

export type MetricasTop5Row = {
  posicion: number;
  slug: string;
  nombre: string;
  score_promedio: number;
  alerta: boolean;
};

export type MetricasAlertaRow = {
  alerta_id: number;
  topico_slug: string;
  topico_nombre: string;
  anio: number;
  mes: number;
  score_actual: number;
  umbral_usado: number;
  mensaje: string;
  generada_en: string;
};

async function parseJsonEnvelope<T>(
  res: Response,
): Promise<DashboardEnvelope<T>> {
  let body: DashboardEnvelope<T>;
  try {
    body = (await res.json()) as DashboardEnvelope<T>;
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
}

export async function fetchMetricasKpis(
  hotelId: number,
  anio: number,
  mes: number,
): Promise<DashboardEnvelope<MetricasKpisData>> {
  const base = getDashboardApiBaseUrl();
  const q = new URLSearchParams({
    hotel_id: String(hotelId),
    anio: String(anio),
    mes: String(mes),
  });
  const url = `${base}/api/v1/metricas/kpis?${q.toString()}`;
  try {
    const res = await fetchWithAuth(url, { cache: "no-store" });
    return parseJsonEnvelope<MetricasKpisData>(res);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Error de red";
    return {
      ok: false,
      data: null,
      error: { codigo: "RED", mensaje: msg },
    };
  }
}

export async function fetchMetricasTopicos(
  hotelId: number,
  anio: number,
  mes: number,
): Promise<DashboardEnvelope<MetricasTopicoRow[]>> {
  const base = getDashboardApiBaseUrl();
  const q = new URLSearchParams({
    hotel_id: String(hotelId),
    anio: String(anio),
    mes: String(mes),
  });
  const url = `${base}/api/v1/metricas/topicos?${q.toString()}`;
  try {
    const res = await fetchWithAuth(url, { cache: "no-store" });
    return parseJsonEnvelope<MetricasTopicoRow[]>(res);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Error de red";
    return {
      ok: false,
      data: null,
      error: { codigo: "RED", mensaje: msg },
    };
  }
}

export async function fetchMetricasTopicosTop5(
  hotelId: number,
  anio: number,
  mes: number,
): Promise<DashboardEnvelope<MetricasTop5Row[]>> {
  const base = getDashboardApiBaseUrl();
  const q = new URLSearchParams({
    hotel_id: String(hotelId),
    anio: String(anio),
    mes: String(mes),
  });
  const url = `${base}/api/v1/metricas/topicos/top5?${q.toString()}`;
  try {
    const res = await fetchWithAuth(url, { cache: "no-store" });
    return parseJsonEnvelope<MetricasTop5Row[]>(res);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Error de red";
    return {
      ok: false,
      data: null,
      error: { codigo: "RED", mensaje: msg },
    };
  }
}

export async function fetchMetricasAlertas(
  hotelId: number,
  resuelta = false,
): Promise<DashboardEnvelope<MetricasAlertaRow[]>> {
  const base = getDashboardApiBaseUrl();
  const q = new URLSearchParams({
    hotel_id: String(hotelId),
    resuelta: resuelta ? "true" : "false",
  });
  const url = `${base}/api/v1/metricas/alertas?${q.toString()}`;
  try {
    const res = await fetchWithAuth(url, { cache: "no-store" });
    return parseJsonEnvelope<MetricasAlertaRow[]>(res);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Error de red";
    return {
      ok: false,
      data: null,
      error: { codigo: "RED", mensaje: msg },
    };
  }
}

export type MetricasSentimientoMensualRow = {
  anio: number;
  mes: number;
  score_promedio: number;
  total_reviews: number;
};

const TOPIC_ICON_BY_SLUG: Record<string, string> = {
  ubicacion: "📍",
  localizacion: "📍",
  servicio: "🤝",
  atencion: "🤝",
  personal: "🤝",
  habitaciones: "🛏️",
  habitacion: "🛏️",
  confort: "🛏️",
  limpieza: "🧹",
  alimentacion: "🍽️",
  comida: "🍽️",
  restaurante: "🍽️",
  estacionamiento: "🅿️",
  instalaciones: "🏢",
  wifi: "📶",
  internet: "📶",
  ruido: "🔇",
  precio: "💰",
  calidad_precio: "💰",
  relacion_calidad_precio: "💰",
};

function pickTopicIcon(slug: string, nombre: string): string {
  const slugKey = slug.trim().toLowerCase();
  if (slugKey in TOPIC_ICON_BY_SLUG) {
    return TOPIC_ICON_BY_SLUG[slugKey];
  }
  const normalizedName = nombre.trim().toLowerCase();
  for (const [key, icon] of Object.entries(TOPIC_ICON_BY_SLUG)) {
    if (normalizedName.includes(key.replaceAll("_", " "))) {
      return icon;
    }
  }
  return "🧩";
}

function getCategoryPaletteByScore(score: number): Pick<
  CategoryScore,
  "barColorClass" | "scoreTextClass"
> {
  if (score >= 80) {
    return {
      barColorClass: "bg-tertiary",
      scoreTextClass: "text-tertiary",
    };
  }
  if (score >= 70) {
    return {
      barColorClass: "bg-secondary",
      scoreTextClass: "text-secondary",
    };
  }
  if (score >= 65) {
    return {
      barColorClass: "bg-warn-orange",
      scoreTextClass: "text-warn-orange",
    };
  }
  return {
    barColorClass: "bg-error",
    scoreTextClass: "text-error",
  };
}

function formatCategoryDelta(
  cambioPct: number,
  tendencia: string,
  alerta: boolean,
): Pick<CategoryScore, "deltaLabel" | "deltaTextClass" | "highlight"> {
  const t = tendencia.trim().toLowerCase();
  const safeCambio = Number.isFinite(cambioPct) ? cambioPct : 0;
  const abs = Math.abs(safeCambio).toFixed(1);
  const arrow = t === "down" ? "▼" : t === "up" ? "▲" : "▶";
  const sign = safeCambio >= 0 ? "+" : "-";
  const isNegativeTrend = t === "down" || safeCambio < 0;

  return {
    deltaLabel: `${arrow} ${sign}${abs}%${alerta ? " ⚠️" : ""}`,
    deltaTextClass: isNegativeTrend ? "text-error" : "text-tertiary",
    highlight: alerta ? "error-border" : undefined,
  };
}

function insightPillForStrengthScore(score: number): InsightRank["pillClass"] {
  const s = Math.round(score * 10) / 10;
  return s >= 75 ? "tertiary" : "warn";
}

function insightPillForPainScore(score: number): InsightRank["pillClass"] {
  const s = Math.round(score * 10) / 10;
  if (s < 65) return "error";
  if (s < 75) return "warn";
  return "tertiary";
}

/**
 * Fortalezas: tópicos con menciones, orden descendente por score (ancla mensual).
 * Pain points: top 5 críticos del backend (menor score primero).
 */
export function buildTopInsightsFromMetricas(
  topicos: MetricasTopicoRow[],
  top5: MetricasTop5Row[],
): { strengths: InsightRank[]; painPoints: InsightRank[] } {
  const strengths: InsightRank[] = [...topicos]
    .filter((row) => row.total_menciones > 0)
    .sort((a, b) => b.score_promedio - a.score_promedio)
    .slice(0, 5)
    .map((row, i) => {
      const score = Math.round(row.score_promedio * 10) / 10;
      return {
        rank: i + 1,
        name: row.nombre,
        score,
        pillClass: insightPillForStrengthScore(row.score_promedio),
      };
    });

  const painPoints: InsightRank[] = top5.map((row) => ({
    rank: row.posicion,
    name: row.nombre,
    score: Math.round(row.score_promedio * 10) / 10,
    pillClass: insightPillForPainScore(row.score_promedio),
  }));

  return { strengths, painPoints };
}

export type FetchTopInsightsResult =
  | { ok: true; data: { strengths: InsightRank[]; painPoints: InsightRank[] } }
  | { ok: false; error: string };

export async function fetchTopInsightsForPeriod(
  period: DashboardPeriod,
  hotelId: number,
): Promise<FetchTopInsightsResult> {
  const window = getHeroMonthWindow(period);
  if (window.length === 0) {
    return { ok: false, error: "Ventana de período vacía." };
  }
  const anchor = window[window.length - 1];
  const [topicosEnv, top5Env] = await Promise.all([
    fetchMetricasTopicos(hotelId, anchor.anio, anchor.mes),
    fetchMetricasTopicosTop5(hotelId, anchor.anio, anchor.mes),
  ]);
  if (!topicosEnv.ok) {
    return {
      ok: false,
      error: topicosEnv.error?.mensaje ?? "No se pudieron cargar los tópicos.",
    };
  }
  if (!top5Env.ok) {
    return {
      ok: false,
      error: top5Env.error?.mensaje ?? "No se pudo cargar el top de pain points.",
    };
  }

  const { strengths, painPoints } = buildTopInsightsFromMetricas(
    topicosEnv.data ?? [],
    top5Env.data ?? [],
  );

  return { ok: true, data: { strengths, painPoints } };
}

function painPointIndexTag(score: number): PainPointCard["tag"] {
  const s = Math.round(score * 10) / 10;
  if (s < 65) return "crit";
  if (s < 75) return "warn";
  return "ok";
}

/**
 * Tarjetas del índice de pain points: top 5 mensual del backend + delta desde
 * `metricas/topicos` (mismo mes ancla que el resto del dashboard).
 */
export function buildPainPointIndexCardsFromMetricas(
  topicos: MetricasTopicoRow[],
  top5: MetricasTop5Row[],
): PainPointCard[] {
  const bySlug = new Map(
    topicos.map((t) => [t.slug.trim().toLowerCase(), t] as const),
  );

  return top5.map((row) => {
    const topico = bySlug.get(row.slug.trim().toLowerCase());
    const cambio = topico?.cambio_pct_vs_anterior ?? 0;
    const tendencia = topico?.tendencia ?? "stable";
    const alerta = Boolean(row.alerta || topico?.alerta);
    const score = Math.max(
      0,
      Math.min(100, Math.round(row.score_promedio * 10) / 10),
    );
    const { deltaLabel } = formatCategoryDelta(cambio, tendencia, alerta);

    return {
      slug: row.slug,
      icon: pickTopicIcon(row.slug, row.nombre),
      name: row.nombre,
      score,
      deltaLabel,
      tag: painPointIndexTag(score),
    };
  });
}

export type FetchPainPointsIndexResult =
  | { ok: true; data: PainPointCard[] }
  | { ok: false; error: string };

export async function fetchPainPointsIndexForPeriod(
  period: DashboardPeriod,
  hotelId: number,
): Promise<FetchPainPointsIndexResult> {
  const window = getHeroMonthWindow(period);
  if (window.length === 0) {
    return { ok: false, error: "Ventana de período vacía." };
  }
  const anchor = window[window.length - 1];
  const [topicosEnv, top5Env] = await Promise.all([
    fetchMetricasTopicos(hotelId, anchor.anio, anchor.mes),
    fetchMetricasTopicosTop5(hotelId, anchor.anio, anchor.mes),
  ]);
  if (!topicosEnv.ok) {
    return {
      ok: false,
      error: topicosEnv.error?.mensaje ?? "No se pudieron cargar los tópicos.",
    };
  }
  if (!top5Env.ok) {
    return {
      ok: false,
      error: top5Env.error?.mensaje ?? "No se pudo cargar el índice de pain points.",
    };
  }

  const cards = buildPainPointIndexCardsFromMetricas(
    topicosEnv.data ?? [],
    top5Env.data ?? [],
  );
  return { ok: true, data: cards };
}

export function buildCategoryScoresFromMetricas(
  topicos: MetricasTopicoRow[],
): CategoryScore[] {
  return [...topicos]
    .filter((row) => row.total_menciones > 0)
    .sort((a, b) => b.score_promedio - a.score_promedio)
    .map((row) => {
      const score = Math.max(
        0,
        Math.min(100, Math.round(row.score_promedio * 10) / 10),
      );
      return {
        icon: pickTopicIcon(row.slug, row.nombre),
        name: row.nombre,
        score,
        ...getCategoryPaletteByScore(score),
        ...formatCategoryDelta(
          row.cambio_pct_vs_anterior,
          row.tendencia,
          row.alerta,
        ),
      };
    });
}

const MES_CORTO = [
  "Ene",
  "Feb",
  "Mar",
  "Abr",
  "May",
  "Jun",
  "Jul",
  "Ago",
  "Sep",
  "Oct",
  "Nov",
  "Dic",
] as const;

function formatYearMonthYm(ym: YearMonth): string {
  return `${ym.anio}-${String(ym.mes).padStart(2, "0")}`;
}

function labelRangoVentana(desde: YearMonth, hasta: YearMonth): string {
  const a = `${MES_CORTO[desde.mes - 1]} ${desde.anio}`;
  const b = `${MES_CORTO[hasta.mes - 1]} ${hasta.anio}`;
  return `${a} → ${b}`;
}

/**
 * Convierte filas del DashboardBackend en la forma esperada por `TrendChart`.
 */
export function sentimientoMensualRowsToTrendSeries(
  rows: MetricasSentimientoMensualRow[],
  ventana: { desde: YearMonth; hasta: YearMonth },
): TrendSeries {
  const sorted = [...rows].sort((x, y) => {
    if (x.anio !== y.anio) return x.anio - y.anio;
    return x.mes - y.mes;
  });
  const months = sorted.map(
    (r) => `${MES_CORTO[r.mes - 1]} ${r.anio}`,
  );
  const values = sorted.map((r) =>
    typeof r.score_promedio === "number" && !Number.isNaN(r.score_promedio)
      ? Math.round(r.score_promedio * 10) / 10
      : 0,
  );

  return {
    title: "Comportamiento Mensual del Sentimiento",
    dateRangeLabel: labelRangoVentana(ventana.desde, ventana.hasta),
    months,
    values,
  };
}

export async function fetchMetricasSentimientoMensual(
  hotelId: number,
  desde: string,
  hasta: string,
): Promise<DashboardEnvelope<MetricasSentimientoMensualRow[]>> {
  const base = getDashboardApiBaseUrl();
  const q = new URLSearchParams({
    hotel_id: String(hotelId),
    desde,
    hasta,
  });
  const url = `${base}/api/v1/metricas/sentimiento-mensual?${q.toString()}`;
  try {
    const res = await fetchWithAuth(url, { cache: "no-store" });
    return parseJsonEnvelope<MetricasSentimientoMensualRow[]>(res);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Error de red";
    return {
      ok: false,
      data: null,
      error: { codigo: "RED", mensaje: msg },
    };
  }
}

export type FetchTrendSeriesResult =
  | { status: "ok"; data: TrendSeries }
  | { status: "error"; message: string }
  | { status: "empty" };

function safePercent(numerator: number, denominator: number): number {
  if (denominator <= 0) return 0;
  return Math.round((numerator / denominator) * 100);
}

function formatTrendLabel(value: number): string {
  const abs = Math.abs(value).toFixed(1);
  if (value < 0) return `▼ -${abs}%`;
  if (value > 0) return `▲ +${abs}%`;
  return `▶ ${abs}%`;
}

function parseIsoDate(value: string): Date | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function countRecentAlerts(alerts: MetricasAlertaRow[], days: number): number {
  const now = Date.now();
  const cutoff = now - days * 24 * 60 * 60 * 1000;
  return alerts.reduce((acc, alert) => {
    const date = parseIsoDate(alert.generada_en);
    if (date === null) return acc;
    return date.getTime() >= cutoff ? acc + 1 : acc;
  }, 0);
}

export function buildRiskAlertsFromMetricas(
  topicos: MetricasTopicoRow[],
  alertas: MetricasAlertaRow[],
): RiskAlerts {
  const rowsWithMentions = topicos.filter((row) => row.total_menciones > 0);
  const alertRows = rowsWithMentions
    .filter((row) => row.alerta)
    .sort((a, b) => a.score_promedio - b.score_promedio);
  const umbral =
    alertas.find((a) => Number.isFinite(a.umbral_usado))?.umbral_usado ?? 65;
  const criticalCutoff = umbral - 3;
  const tableRows: RiskAlerts["tableRows"] = alertRows.map((row) => {
    const scoreRounded = Math.round(row.score_promedio * 10) / 10;
    const critical = scoreRounded < criticalCutoff;
    return {
      topic: row.nombre,
      score: scoreRounded,
      status: critical ? "crit" : "warn",
      trendLabel: formatTrendLabel(row.cambio_pct_vs_anterior),
      dotClass: critical ? "error" : "warn-orange",
    };
  });

  const topicsInRisk = tableRows.length;
  const totalTopics = rowsWithMentions.length;
  const riskPercent = safePercent(topicsInRisk, totalTopics);
  const criticalPercent = safePercent(
    tableRows.filter((row) => row.status === "crit").length,
    topicsInRisk,
  );

  return {
    sectionLabel: "🚨 Riesgo Reputacional · Alertas Activas",
    summary: {
      topicsInAlert: topicsInRisk,
      criticalPercent,
      newIn7d: countRecentAlerts(alertas, 7),
    },
    tableRows,
    donut: {
      centerPercent: riskPercent,
      centerSubtext: `bajo umbral\n${Math.round(umbral)}%`,
      caption: `${topicsInRisk} de ${totalTopics} tópicos en zona de riesgo`,
    },
  };
}

export type FetchRiskAlertsResult =
  | { ok: true; data: RiskAlerts }
  | { ok: false; error: string };

export async function fetchTrendSeriesForPeriod(
  period: DashboardPeriod,
  hotelId: number,
): Promise<FetchTrendSeriesResult> {
  const window = getHeroMonthWindow(period);
  if (window.length === 0) {
    return { status: "empty" };
  }
  const desdeYm = window[0];
  const hastaYm = window[window.length - 1];
  const desde = formatYearMonthYm(desdeYm);
  const hasta = formatYearMonthYm(hastaYm);

  const env = await fetchMetricasSentimientoMensual(hotelId, desde, hasta);
  if (!env.ok) {
    return {
      status: "error",
      message:
        env.error?.mensaje ??
        `No se pudo cargar la serie (${desde} … ${hasta}).`,
    };
  }

  const rows = env.data ?? [];
  if (rows.length === 0) {
    return { status: "empty" };
  }

  return {
    status: "ok",
    data: sentimientoMensualRowsToTrendSeries(rows, {
      desde: desdeYm,
      hasta: hastaYm,
    }),
  };
}

export async function fetchRiskAlertsForPeriod(
  period: DashboardPeriod,
  hotelId: number,
): Promise<FetchRiskAlertsResult> {
  const window = getHeroMonthWindow(period);
  if (window.length === 0) {
    return { ok: false, error: "Ventana de período vacía." };
  }
  const anchor = window[window.length - 1];
  const [topicosEnv, alertasEnv] = await Promise.all([
    fetchMetricasTopicos(hotelId, anchor.anio, anchor.mes),
    fetchMetricasAlertas(hotelId, false),
  ]);
  if (!topicosEnv.ok) {
    return {
      ok: false,
      error: topicosEnv.error?.mensaje ?? "No se pudieron cargar los tópicos.",
    };
  }
  if (!alertasEnv.ok) {
    return {
      ok: false,
      error: alertasEnv.error?.mensaje ?? "No se pudieron cargar las alertas.",
    };
  }

  return {
    ok: true,
    data: buildRiskAlertsFromMetricas(
      topicosEnv.data ?? [],
      alertasEnv.data ?? [],
    ),
  };
}

function formatDeltaBadge(cambioPct: number, tendencia: string): string {
  const sign = cambioPct >= 0 ? "+" : "";
  const abs = Math.abs(cambioPct).toFixed(2);
  const t = tendencia.toLowerCase();
  if (t === "down") {
    return `▼ ${sign}${abs}% vs período anterior`;
  }
  if (t === "up") {
    return `▲ ${sign}${abs}% vs período anterior`;
  }
  return `▶ ${sign}${cambioPct.toFixed(2)}% vs período anterior`;
}

function variationSubtext(tendencia: string): string {
  const t = tendencia.toLowerCase();
  if (t === "up") return "Tendencia al alza\nrespecto al mes anterior";
  if (t === "down") return "Tendencia a la baja\nrespecto al mes anterior";
  return "Estabilidad\nrespecto al mes anterior";
}

function labelFromHeroAreaSubtext(subtext: string): string {
  const first = subtext.split(" · ")[0]?.trim() ?? subtext;
  return first.replace(/^📍\s*/, "").replace(/^🔇\s*/, "").trim();
}

/**
 * Segundo peor tópico: `top5[1]` si existe; si no, el siguiente más bajo entre
 * tópicos con menciones excluyendo el peor del `top5[0]`; si `top5` está vacío,
 * el segundo de la lista ordenada por score ascendente.
 */
function pickSecondWorstTopic(
  top5: MetricasTop5Row[],
  topicos: MetricasTopicoRow[],
): { nombre: string; score: number } | null {
  if (top5.length >= 2) {
    const r = top5[1];
    return {
      nombre: r.nombre,
      score: Math.round(r.score_promedio * 10) / 10,
    };
  }

  const rows = topicos.filter((t) => t.total_menciones > 0);
  const sorted = [...rows].sort((a, b) => a.score_promedio - b.score_promedio);

  if (top5.length === 1) {
    const ws = top5[0].slug.trim().toLowerCase();
    for (const row of sorted) {
      if (row.slug.trim().toLowerCase() === ws) continue;
      return {
        nombre: row.nombre,
        score: Math.round(row.score_promedio * 10) / 10,
      };
    }
    return null;
  }

  if (sorted.length >= 2) {
    const r = sorted[1];
    return {
      nombre: r.nombre,
      score: Math.round(r.score_promedio * 10) / 10,
    };
  }
  return null;
}

function scoreBandClass(score: number): ExecutiveKpi["valueClass"] {
  if (score >= 75) return "tertiary";
  if (score >= 65) return "primary";
  return "error";
}

/** Misma cadena que `buildHeroKpisFromMetricas` cuando no hay tópicos con menciones. */
const SIN_METRICAS_TOPICO = "Sin métricas por tópico";

function hasHeroTopicMetrics(
  area: HeroKpis["bestArea"] | HeroKpis["worstArea"],
): boolean {
  return area.subtext.trim() !== SIN_METRICAS_TOPICO;
}

/**
 * Los 6 KPIs del Resumen ejecutivo / CEI a partir del hero y del mes ancla
 * (mismos datos que `fetchHeroKpisForPeriod`).
 */
export function buildExecutiveKpisFromMetricas(
  hero: HeroKpis,
  anchorKpi: MetricasKpisData,
  topicos: MetricasTopicoRow[],
  top5: MetricasTop5Row[],
): ExecutiveKpi[] {
  const deltaClass: ExecutiveKpi["valueClass"] =
    hero.deltaPercent >= 0 ? "tertiary" : "error";
  const alertCount = Math.max(0, Math.round(anchorKpi.topicos_con_alerta));
  const alertClass: ExecutiveKpi["valueClass"] =
    alertCount > 0 ? "error" : "tertiary";

  const hasBest = hasHeroTopicMetrics(hero.bestArea);
  const hasWorst = hasHeroTopicMetrics(hero.worstArea);
  const bestScore = Math.round(hero.bestArea.score * 10) / 10;
  const bestLabel = labelFromHeroAreaSubtext(hero.bestArea.subtext);
  const worstScore = Math.round(hero.worstArea.score * 10) / 10;
  const worstLabel = labelFromHeroAreaSubtext(hero.worstArea.subtext);

  const second = pickSecondWorstTopic(top5, topicos);
  const sign = hero.deltaPercent >= 0 ? "+" : "";

  return [
    {
      label: "Sentimiento global",
      value: `${hero.sentimentScore}%`,
      subtext: "Percepción global del huésped",
      valueClass: "primary",
    },
    {
      label: "Variación vs mes anterior",
      value: `${sign}${hero.deltaPercent.toFixed(2)}%`,
      subtext: hero.variationCard.subtext.replaceAll("\n", " · "),
      valueClass: deltaClass,
    },
    {
      label: "Tópicos en alerta",
      value: String(alertCount),
      subtext: "Por debajo del umbral definido",
      valueClass: alertClass,
    },
    {
      label: "Mejor categoría",
      value: hasBest ? `${bestScore}%` : "—",
      subtext: hasBest ? bestLabel : SIN_METRICAS_TOPICO,
      valueClass: hasBest ? scoreBandClass(bestScore) : "tertiary",
    },
    {
      label: "Queja principal",
      value: hasWorst ? `${worstScore}%` : "—",
      subtext: hasWorst ? worstLabel : SIN_METRICAS_TOPICO,
      valueClass: hasWorst ? "error" : "tertiary",
    },
    {
      label: "Segundo foco crítico",
      value: second ? `${second.score}%` : "—",
      subtext: second ? second.nombre : "Sin segundo tópico",
      valueClass: second ? scoreBandClass(second.score) : "tertiary",
    },
  ];
}

export function buildHeroKpisFromMetricas(
  kpisWindow: MetricasKpisData[],
  anchorKpis: MetricasKpisData,
  topicos: MetricasTopicoRow[] | null,
  top5: MetricasTop5Row[] | null,
): HeroKpis {
  const sp = anchorKpis.sentimiento_promedio;
  const deltaPercent = sp.cambio_pct;

  let sentimentScore = 0;
  if (kpisWindow.length > 0) {
    const sum = kpisWindow.reduce(
      (acc, k) => acc + k.sentimiento_promedio.score,
      0,
    );
    sentimentScore = Math.round((sum / kpisWindow.length) * 10) / 10;
  }

  const deltaBadgeText = formatDeltaBadge(deltaPercent, sp.tendencia);
  const sign = deltaPercent >= 0 ? "+" : "";
  const variationValue = `${sign}${deltaPercent.toFixed(2)}%`;

  const rows =
    topicos?.filter((r) => r.total_menciones > 0) ?? [];
  let bestArea: HeroKpis["bestArea"] = {
    label: "Mejor Área",
    score: 0,
    subtext: "Sin métricas por tópico",
  };
  if (rows.length > 0) {
    const best = rows.reduce((a, b) =>
      a.score_promedio >= b.score_promedio ? a : b,
    );
    bestArea = {
      label: "Mejor Área",
      score: Math.round(best.score_promedio * 10) / 10,
      subtext: `📍 ${best.nombre}`,
    };
  }

  let worstArea: HeroKpis["worstArea"] = {
    label: "Peor Área",
    score: 0,
    subtext: "Sin métricas por tópico",
  };
  const worstFromTop5 = top5?.[0];
  if (worstFromTop5) {
    worstArea = {
      label: "Peor Área",
      score: Math.round(worstFromTop5.score_promedio * 10) / 10,
      subtext: `🔇 ${worstFromTop5.nombre} · Pain Point #1`,
    };
  } else if (rows.length > 0) {
    const worst = rows.reduce((a, b) =>
      a.score_promedio <= b.score_promedio ? a : b,
    );
    worstArea = {
      label: "Peor Área",
      score: Math.round(worst.score_promedio * 10) / 10,
      subtext: `🔇 ${worst.nombre} · Pain Point #1`,
    };
  }

  return {
    sentimentScore,
    sentimentLabel: "Customer Sentiment Score",
    sentimentSubtext: "Percepción global del huésped",
    deltaPercent,
    deltaBadgeText,
    variationCard: {
      label: "Variación Δ%",
      value: variationValue,
      subtext: variationSubtext(sp.tendencia),
    },
    bestArea,
    worstArea,
  };
}

export type FetchHeroKpisResult =
  | { ok: true; data: HeroKpis; executiveKpis: ExecutiveKpi[] }
  | { ok: false; error: string };

export async function fetchHeroKpisForPeriod(
  period: DashboardPeriod,
  hotelId: number,
): Promise<FetchHeroKpisResult> {
  const window = getHeroMonthWindow(period);
  if (window.length === 0) {
    return { ok: false, error: "Ventana de período vacía." };
  }

  const kpisEnvelopes = await Promise.all(
    window.map((m) => fetchMetricasKpis(hotelId, m.anio, m.mes)),
  );
  const porMes: { ym: YearMonth; kpi: MetricasKpisData }[] = [];
  for (let i = 0; i < kpisEnvelopes.length; i++) {
    const env = kpisEnvelopes[i];
    if (!env.ok) {
      return {
        ok: false,
        error:
          env.error?.mensaje ??
          `No se pudieron cargar KPIs (${window[i].anio}-${window[i].mes}).`,
      };
    }
    porMes.push({
      ym: window[i],
      kpi: env.data ?? KPIS_SIN_FILA,
    });
  }

  const mesesConDatos = porMes.filter((row) =>
    kpiTieneDatosMensuales(row.kpi),
  );
  const kpisParaPromedio = mesesConDatos.map((row) => row.kpi);

  const ultimoConDatos = mesesConDatos[mesesConDatos.length - 1];
  const finVentana = porMes[porMes.length - 1];
  const ancla: { ym: YearMonth; kpi: MetricasKpisData } =
    ultimoConDatos ?? finVentana;

  const [topicosEnv, top5Env] = await Promise.all([
    fetchMetricasTopicos(hotelId, ancla.ym.anio, ancla.ym.mes),
    fetchMetricasTopicosTop5(hotelId, ancla.ym.anio, ancla.ym.mes),
  ]);

  if (!topicosEnv.ok) {
    return {
      ok: false,
      error: topicosEnv.error?.mensaje ?? "Error al cargar tópicos.",
    };
  }
  if (!top5Env.ok) {
    return {
      ok: false,
      error: top5Env.error?.mensaje ?? "Error al cargar top 5 de tópicos.",
    };
  }

  const hero = buildHeroKpisFromMetricas(
    kpisParaPromedio,
    ancla.kpi,
    topicosEnv.data ?? [],
    top5Env.data ?? [],
  );
  const executiveKpis = buildExecutiveKpisFromMetricas(
    hero,
    ancla.kpi,
    topicosEnv.data ?? [],
    top5Env.data ?? [],
  );

  return {
    ok: true,
    data: hero,
    executiveKpis,
  };
}

function yearMonthToIsoDateStart(ym: YearMonth): string {
  return `${ym.anio}-${String(ym.mes).padStart(2, "0")}-01`;
}

function yearMonthToIsoDateEnd(ym: YearMonth): string {
  const nextMonth = new Date(ym.anio, ym.mes, 1);
  const end = new Date(nextMonth.getTime() - 24 * 60 * 60 * 1000);
  return `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(
    end.getDate(),
  ).padStart(2, "0")}`;
}

function average(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((acc, n) => acc + n, 0) / values.length;
}

function formatReliability(
  reviewsTotal: number,
  avgConfidencePct: number | null,
  sampledReviews: number,
): Pick<DataStrength, "reliabilityValue" | "reliabilitySubtext"> {
  if (avgConfidencePct !== null) {
    const rounded = Math.round(avgConfidencePct);
    const level =
      rounded >= 80 ? "Alta" : rounded >= 65 ? "Media" : "Baja";
    const scope =
      sampledReviews > 0
        ? `muestra de ${sampledReviews} reviews`
        : "muestra disponible";
    return {
      reliabilityValue: level,
      reliabilitySubtext: `Confianza media del modelo: ${rounded}% (${scope})`,
    };
  }

  if (reviewsTotal >= 1000) {
    return {
      reliabilityValue: "Alta",
      reliabilitySubtext: "n >= 1,000 reviews en la ventana",
    };
  }
  if (reviewsTotal >= 300) {
    return {
      reliabilityValue: "Media",
      reliabilitySubtext: "n >= 300 reviews en la ventana",
    };
  }
  return {
    reliabilityValue: "Baja",
    reliabilitySubtext: "Muestra limitada en la ventana",
  };
}

export type FetchDataStrengthResult =
  | { ok: true; data: DataStrength }
  | { ok: false; error: string };

export async function fetchDataStrengthForPeriod(
  period: DashboardPeriod,
  hotelId: number,
): Promise<FetchDataStrengthResult> {
  const window = getHeroMonthWindow(period);
  if (window.length === 0) {
    return { ok: false, error: "Ventana de período vacía." };
  }

  const kpisEnvelopes = await Promise.all(
    window.map((m) => fetchMetricasKpis(hotelId, m.anio, m.mes)),
  );

  const reviewsByMonth: number[] = [];
  for (let i = 0; i < kpisEnvelopes.length; i++) {
    const env = kpisEnvelopes[i];
    if (!env.ok) {
      return {
        ok: false,
        error:
          env.error?.mensaje ??
          `No se pudieron cargar KPIs (${window[i].anio}-${window[i].mes}).`,
      };
    }
    reviewsByMonth.push(env.data?.reviews_analizadas ?? 0);
  }

  const reviewsTotal = reviewsByMonth.reduce((acc, n) => acc + n, 0);
  const reviewsPerMonth = Math.round(average(reviewsByMonth));

  const desde = yearMonthToIsoDateStart(window[0]);
  const hasta = yearMonthToIsoDateEnd(window[window.length - 1]);
  const reviewsEnv = await fetchDashboardReviews({
    hotel_id: hotelId,
    fecha_desde: desde,
    fecha_hasta: hasta,
    page: 1,
    page_size: 100,
    orden: "fecha_desc",
  });

  if (!reviewsEnv.ok) {
    return {
      ok: false,
      error: reviewsEnv.error?.mensaje ?? "No se pudieron cargar reviews.",
    };
  }

  const reviewItems = reviewsEnv.data?.items ?? [];
  const plataformas = new Set(
    reviewItems
      .map((item) => item.plataforma?.trim())
      .filter((p): p is string => Boolean(p)),
  );
  const platformLabel =
    plataformas.size > 0
      ? Array.from(plataformas).join(" · ")
      : "Sin plataforma registrada";

  const confidenceValues = reviewItems
    .map((item) => item.prediccion.confianza)
    .filter((v): v is number => typeof v === "number" && !Number.isNaN(v))
    .map((v) => v * 100);
  const avgConfidence =
    confidenceValues.length > 0 ? average(confidenceValues) : null;

  const reliability = formatReliability(
    reviewsTotal,
    avgConfidence,
    reviewItems.length,
  );
  const periodLabel =
    period === "month"
      ? "en el período"
      : period === "quarter"
        ? "en el trimestre"
        : "en el semestre";

  return {
    ok: true,
    data: {
      reviewsTotal,
      reviewsTotalLabel: `Total ${periodLabel}`,
      reviewsPerMonth,
      reviewsPerMonthLabel: `Promedio mensual (${window.length} meses)`,
      sparklineValues: reviewsByMonth,
      sourceCount: plataformas.size,
      sourcesLabel:
        reviewsTotal > reviewItems.length
          ? `${platformLabel} (muestra reciente)`
          : platformLabel,
      reliabilityLabel: "Confiabilidad",
      reliabilityValue: reliability.reliabilityValue,
      reliabilitySubtext: reliability.reliabilitySubtext,
    },
  };
}
