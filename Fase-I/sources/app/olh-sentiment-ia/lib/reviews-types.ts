/**
 * Tipos de UI del Reviews Explorer (mapeados desde la API del dashboard).
 */

export type TopicScoreTone = "tertiary" | "primary" | "error";

export type ReviewTopicScore = {
  label: string;
  percent: number;
  tone: TopicScoreTone;
};

export type ReviewBorderAccent = "tertiary" | "error" | "primary";

export type ReviewSentimentBadgeVariant = "excellent" | "critical" | "good";

export type ReviewSource =
  | {
      kind: "booking";
      label: string;
      logoUrl: string;
      logoAlt: string;
    }
  | {
      kind: "icon";
      label: string;
      icon: string;
    };

export type ReviewExplorerItem = {
  id: string;
  title: string;
  dateDisplay: string;
  headerIcon: string;
  headerIconMuted: boolean;
  source: ReviewSource;
  body: string;
  borderAccent: ReviewBorderAccent;
  sentimentBadge: {
    percent: number;
    label: string;
    variant: ReviewSentimentBadgeVariant;
  };
  topics: ReviewTopicScore[];
};

export type ReviewsFilterBarData = {
  dateRangeLabel: string;
  sentimentChips: Array<{
    id: string;
    label: string;
    style: "positive" | "neutral" | "critical" | "all";
    /** `null` = sin filtro (Todos). */
    value: "positivo" | "neutro" | "negativo" | null;
  }>;
  themeTags: Array<{ slug: string; label: string; active?: boolean }>;
};

export type ReviewsPageHeader = {
  title: string;
  subtitle: string;
};
