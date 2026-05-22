/**
 * Datos mock del Executive Dashboard — sustituir por respuestas de API.
 */

export type HeroKpis = {
  sentimentScore: number;
  sentimentLabel: string;
  sentimentSubtext: string;
  deltaPercent: number;
  deltaBadgeText: string;
  variationCard: {
    label: string;
    value: string;
    subtext: string;
  };
  bestArea: {
    label: string;
    score: number;
    subtext: string;
  };
  worstArea: {
    label: string;
    score: number;
    subtext: string;
  };
};

export type TrendSeries = {
  title: string;
  dateRangeLabel: string;
  months: string[];
  values: number[];
};

export type DataStrength = {
  reviewsTotal: number;
  reviewsTotalLabel: string;
  reviewsPerMonth: number;
  reviewsPerMonthLabel: string;
  sparklineValues: number[];
  sourceCount: number;
  sourcesLabel: string;
  reliabilityLabel: string;
  reliabilityValue: string;
  reliabilitySubtext: string;
};

export type RiskTopicRow = {
  topic: string;
  score: number;
  status: "crit" | "warn";
  trendLabel: string;
  dotClass: "error" | "warn-orange";
};

export type RiskAlerts = {
  sectionLabel: string;
  summary: {
    topicsInAlert: number;
    criticalPercent: number;
    newIn7d: number;
  };
  tableRows: RiskTopicRow[];
  donut: {
    centerPercent: number;
    centerSubtext: string;
    caption: string;
  };
};

export type CategoryScore = {
  icon: string;
  name: string;
  score: number;
  barColorClass: string;
  scoreTextClass: string;
  deltaLabel: string;
  deltaTextClass: string;
  highlight?: "error-border" | "error-bg";
};

export type InsightRank = {
  rank: number;
  name: string;
  score: number;
  pillClass: "tertiary" | "error" | "warn";
};

export type PainPointCard = {
  /** Slug estable para keys en listas (API). */
  slug: string;
  icon: string;
  name: string;
  score: number;
  deltaLabel: string;
  tag: "crit" | "warn" | "ok";
};

export type ExecutiveKpi = {
  label: string;
  value: string;
  subtext: string;
  valueClass: "primary" | "tertiary" | "error";
};

export type AdvancedMetric = {
  label: string;
  value: string;
  description: string;
  valueClass: string;
};

export type AdvancedMetricsBlock = {
  row1: AdvancedMetric[];
  row2: AdvancedMetric[];
};

export const heroKpis: HeroKpis = {
  sentimentScore: 72,
  sentimentLabel: "Customer Sentiment Score",
  sentimentSubtext: "Percepción global del huésped",
  deltaPercent: 1.42,
  deltaBadgeText: "▲ +1.42% vs período anterior",
  variationCard: {
    label: "Variación Δ%",
    value: "+1.42%",
    subtext: "Mejora constante\n3 meses consecutivos",
  },
  bestArea: {
    label: "Mejor Área",
    score: 88,
    subtext: "📍 Ubicación",
  },
  worstArea: {
    label: "Peor Área",
    score: 58,
    subtext: "🔇 Ruido · Pain Point #1",
  },
};

export const trendSeries: TrendSeries = {
  title: "Comportamiento Mensual del Sentimiento",
  dateRangeLabel: "May 2025 → Abr 2026",
  months: [
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
    "Ene",
    "Feb",
    "Mar",
    "Abr",
  ],
  values: [65, 67, 68, 70, 69, 72, 73, 71, 73, 74, 72, 72],
};

export const dataStrength: DataStrength = {
  reviewsTotal: 1247,
  reviewsTotalLabel: "Total acumulado",
  reviewsPerMonth: 104,
  reviewsPerMonthLabel: "Promedio últimos 12 meses",
  sparklineValues: [78, 92, 105, 88, 115, 98, 120, 110, 95, 130, 108, 112],
  sourceCount: 4,
  sourcesLabel: "Google · Booking · TripAdvisor · Expedia",
  reliabilityLabel: "Confiabilidad",
  reliabilityValue: "Alta",
  reliabilitySubtext: "n > 1,000 reviews",
};

export const riskAlerts: RiskAlerts = {
  sectionLabel: "🚨 Riesgo Reputacional · Alertas Activas",
  summary: {
    topicsInAlert: 4,
    criticalPercent: 40,
    newIn7d: 2,
  },
  tableRows: [
    {
      topic: "Ruido",
      score: 58,
      status: "crit",
      trendLabel: "▼ -5.2%",
      dotClass: "error",
    },
    {
      topic: "WiFi",
      score: 61,
      status: "crit",
      trendLabel: "▼ -2.0%",
      dotClass: "error",
    },
    {
      topic: "Calidad-Precio",
      score: 65,
      status: "warn",
      trendLabel: "▼ -4.2%",
      dotClass: "warn-orange",
    },
    {
      topic: "Instalaciones",
      score: 70,
      status: "warn",
      trendLabel: "▼ -3.0%",
      dotClass: "warn-orange",
    },
  ],
  donut: {
    centerPercent: 40,
    centerSubtext: "bajo umbral\n65%",
    caption: "4 de 10 tópicos en zona de riesgo",
  },
};

export const categoryScores: CategoryScore[] = [
  {
    icon: "📍",
    name: "Ubicación",
    score: 88,
    barColorClass: "bg-tertiary",
    scoreTextClass: "text-tertiary",
    deltaLabel: "▲ +0.5%",
    deltaTextClass: "text-tertiary",
  },
  {
    icon: "🤝",
    name: "Atención Personal",
    score: 82,
    barColorClass: "bg-tertiary",
    scoreTextClass: "text-tertiary",
    deltaLabel: "▲ +2.1%",
    deltaTextClass: "text-tertiary",
  },
  {
    icon: "🛏️",
    name: "Confort Habitación",
    score: 78,
    barColorClass: "bg-secondary",
    scoreTextClass: "text-secondary",
    deltaLabel: "▲ +2.4%",
    deltaTextClass: "text-tertiary",
  },
  {
    icon: "🧹",
    name: "Limpieza",
    score: 75,
    barColorClass: "bg-secondary",
    scoreTextClass: "text-secondary",
    deltaLabel: "▼ -1.2%",
    deltaTextClass: "text-error",
  },
  {
    icon: "🍽️",
    name: "Alimentación",
    score: 74,
    barColorClass: "bg-secondary",
    scoreTextClass: "text-secondary",
    deltaLabel: "▲ +1.8%",
    deltaTextClass: "text-tertiary",
  },
  {
    icon: "🅿️",
    name: "Estacionamiento",
    score: 72,
    barColorClass: "bg-secondary",
    scoreTextClass: "text-secondary",
    deltaLabel: "▲ +1.0%",
    deltaTextClass: "text-tertiary",
  },
  {
    icon: "🏢",
    name: "Instalaciones",
    score: 70,
    barColorClass: "bg-warn-orange",
    scoreTextClass: "text-warn-orange",
    deltaLabel: "▼ -3.0%",
    deltaTextClass: "text-error",
  },
  {
    icon: "💰",
    name: "Calidad-Precio",
    score: 65,
    barColorClass: "bg-error",
    scoreTextClass: "text-error",
    deltaLabel: "▼ -4.2%",
    deltaTextClass: "text-error",
  },
  {
    icon: "📶",
    name: "WiFi",
    score: 61,
    barColorClass: "bg-error",
    scoreTextClass: "text-error",
    deltaLabel: "▼ -2.0%",
    deltaTextClass: "text-error",
  },
  {
    icon: "🔇",
    name: "Ruido",
    score: 58,
    barColorClass: "bg-error",
    scoreTextClass: "text-error",
    deltaLabel: "▼ -5.2% ⚠️",
    deltaTextClass: "text-error",
    highlight: "error-border",
  },
];

export const topStrengths: InsightRank[] = [
  { rank: 1, name: "Ubicación", score: 88, pillClass: "tertiary" },
  { rank: 2, name: "Atención del Personal", score: 82, pillClass: "tertiary" },
  { rank: 3, name: "Confort Habitación", score: 78, pillClass: "tertiary" },
  { rank: 4, name: "Limpieza", score: 75, pillClass: "tertiary" },
];

export const topPainPoints: InsightRank[] = [
  { rank: 1, name: "Ruido", score: 58, pillClass: "error" },
  { rank: 2, name: "WiFi", score: 61, pillClass: "error" },
  { rank: 3, name: "Relación Calidad-Precio", score: 65, pillClass: "warn" },
  { rank: 4, name: "Instalaciones", score: 70, pillClass: "warn" },
];

export const painPointIndexCards: PainPointCard[] = [
  {
    slug: "ruido",
    icon: "🔇",
    name: "Ruido",
    score: 58,
    deltaLabel: "▼ -5.2%",
    tag: "crit",
  },
  {
    slug: "wifi",
    icon: "📶",
    name: "WiFi",
    score: 61,
    deltaLabel: "▼ -2.0%",
    tag: "crit",
  },
  {
    slug: "estacionamiento",
    icon: "🅿️",
    name: "Estacionamiento",
    score: 72,
    deltaLabel: "▲ +1.0%",
    tag: "warn",
  },
];

export const executiveKpis: ExecutiveKpi[] = [
  {
    label: "Sentimiento global",
    value: "72%",
    subtext: "Percepción global del huésped",
    valueClass: "primary",
  },
  {
    label: "Variación vs mes anterior",
    value: "+1.42%",
    subtext: "Tendencia al alza · respecto al mes anterior",
    valueClass: "tertiary",
  },
  {
    label: "Tópicos en alerta",
    value: "4",
    subtext: "Por debajo del umbral definido",
    valueClass: "error",
  },
  {
    label: "Mejor categoría",
    value: "88%",
    subtext: "Ubicación",
    valueClass: "tertiary",
  },
  {
    label: "Queja principal",
    value: "58%",
    subtext: "Ruido",
    valueClass: "error",
  },
  {
    label: "Segundo foco crítico",
    value: "65%",
    subtext: "Calidad-Precio",
    valueClass: "error",
  },
];

export const advancedMetrics: AdvancedMetricsBlock = {
  row1: [
    {
      label: "Weighted Sentiment",
      value: "69.4%",
      description:
        "Ponderado por importancia y volumen de menciones",
      valueClass: "text-chart-teal",
    },
    {
      label: "Topic Impact Score",
      value: "0.73",
      description:
        "Correlación tópicos negativos ↔ caída general (0–1)",
      valueClass: "text-chart-violet",
    },
    {
      label: "Sentiment Volatility",
      value: "4.2σ",
      description:
        "Desviación estándar · Baja volatilidad = estabilidad",
      valueClass: "text-warn-orange",
    },
  ],
  row2: [
    {
      label: "Anomaly Detection",
      value: "2",
      description:
        "Anomalías últimos 30 días: Ruido (-5.2%) y Calidad-Precio (-4.2%)",
      valueClass: "text-error",
    },
    {
      label: "Recovery Prediction",
      value: "~3 meses",
      description:
        "Tiempo estimado para regresar al umbral 65% si se interviene",
      valueClass: "text-tertiary",
    },
  ],
};

export const dashboardFooterNote =
  "Hoteles OLH · Sentiment Intelligence · POC Tesis ICESI · Datos simulados · Abril 2026";
