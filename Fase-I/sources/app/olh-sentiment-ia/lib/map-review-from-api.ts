import type {
  ReviewBorderAccent,
  ReviewExplorerItem,
  ReviewSentimentBadgeVariant,
  ReviewSource,
  ReviewTopicScore,
  TopicScoreTone,
} from "@/lib/reviews-types";
import type { ReviewListItem, TopicoAsignado } from "@/lib/reviews-api";

const BOOKING_LOGO =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuAbIeOb7kWMqfXtpTjc_9_VSxSFZDf-p4to8tEztnKFdBOU82fkt_jEOuIfWrjDaMuYJcSm63ZiIPD32jOKQ9ZPiQoudoVWSBN6bcLs0Y12OlSopwgV1ORJvpAYxgwg2WJ-8li35vOUHO2qhsEl1oqyI-9g0JECuz1TlQoRpvOAkx0jAjobrXQ5HUhq_hP-7UUNCu1U_6gtv0a8MzP69H_gbbkCdlCDsgo5aMmZj2XSGgp2aOhtZISxRbL3P_rjD-DdLbVuGU3YZok";

function truncateTitle(text: string, max = 72): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function mapSource(plataforma: string | null): ReviewSource {
  const label = plataforma?.trim() || "Fuente desconocida";
  const lower = label.toLowerCase();
  if (lower.includes("booking")) {
    return {
      kind: "booking",
      label,
      logoUrl: BOOKING_LOGO,
      logoAlt: label,
    };
  }
  return {
    kind: "icon",
    label,
    icon: "travel_explore",
  };
}

function mapBorderAccent(sentimiento: "positivo" | "negativo" | "neutro"): ReviewBorderAccent {
  switch (sentimiento) {
    case "positivo":
      return "tertiary";
    case "negativo":
      return "error";
    default:
      return "primary";
  }
}

function mapBadge(
  sentimiento: "positivo" | "negativo" | "neutro",
  confianza: number | null,
): { percent: number; label: string; variant: ReviewSentimentBadgeVariant } {
  const pct =
    confianza != null && Number.isFinite(confianza)
      ? Math.round(Math.min(1, Math.max(0, confianza)) * 100)
      : 0;

  if (sentimiento === "negativo") {
    return { percent: pct, label: "Negativo", variant: "critical" };
  }
  if (sentimiento === "neutro") {
    return { percent: pct, label: "Neutro", variant: "good" };
  }
  if (pct >= 85) {
    return { percent: pct, label: "Positivo", variant: "excellent" };
  }
  return { percent: pct, label: "Positivo", variant: "good" };
}

function mapTopicTone(t: TopicoAsignado): TopicScoreTone {
  if (t.sentimiento === "negativo") return "error";
  if (t.sentimiento === "neutro") return "primary";
  if (t.sentimiento === "positivo") return "tertiary";
  const s = t.score_topico;
  if (s == null) return "primary";
  if (s < 0.4) return "error";
  if (s < 0.72) return "primary";
  return "tertiary";
}

function mapTopics(topicos: TopicoAsignado[]): ReviewTopicScore[] {
  return topicos.map((t) => {
    const raw = t.score_topico;
    const percent =
      raw != null && Number.isFinite(raw)
        ? Math.round(Math.min(1, Math.max(0, raw)) * 100)
        : 0;
    return {
      label: t.nombre,
      percent,
      tone: mapTopicTone(t),
    };
  });
}

export function mapReviewListItemToExplorer(item: ReviewListItem): ReviewExplorerItem {
  const title =
    item.titulo?.trim() ||
    truncateTitle(item.texto_limpio.replace(/^["'\s]+|["'\s]+$/g, ""), 72);

  const fecha = new Date(item.fecha_review);
  const dateDisplay = Number.isNaN(fecha.getTime())
    ? item.fecha_review
    : fecha.toLocaleDateString("es-CO", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });

  const pred = item.prediccion;
  const sentimiento = pred?.sentimiento ?? "neutro";

  return {
    id: String(item.review_id),
    title,
    dateDisplay,
    headerIcon: "hotel_class",
    headerIconMuted: sentimiento === "negativo",
    source: mapSource(item.plataforma),
    body: item.texto_limpio,
    borderAccent: mapBorderAccent(sentimiento),
    sentimentBadge: mapBadge(sentimiento, pred?.confianza ?? null),
    topics: mapTopics(item.topicos ?? []),
  };
}
