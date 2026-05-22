import { ReviewsExplorerView } from "@/components/reviews/ReviewsExplorerView";
import {
  fetchDashboardReviews,
  getReviewsExplorerHotelId,
} from "@/lib/reviews-api";
import {
  defaultReviewDateRange,
  formatReviewDateRangeLabel,
  parseIsoDateParam,
} from "@/lib/reviews-date-range";
import { mapReviewListItemToExplorer } from "@/lib/map-review-from-api";
import { buildThemeTagsFromItems } from "@/lib/reviews-theme-tags";
import type { ReviewsFilterBarData, ReviewsPageHeader } from "@/lib/reviews-types";
import type { ReviewsExplorerQuery } from "@/lib/reviews-url";

const header: ReviewsPageHeader = {
  title: "Explorador de reseñas",
  subtitle:
    "Sentimiento global y desglose por tópico según el período y los filtros aplicados.",
};

function parseSearchParams(raw: Record<string, string | string[] | undefined>): {
  page: number;
  sentimiento?: "positivo" | "negativo" | "neutro";
  topico_slug?: string;
  fecha_desde: string;
  fecha_hasta: string;
  query: ReviewsExplorerQuery;
} {
  const pageRaw = typeof raw.page === "string" ? raw.page : undefined;
  const page = Math.max(1, parseInt(pageRaw ?? "1", 10) || 1);

  const senRaw = typeof raw.sentimiento === "string" ? raw.sentimiento : undefined;
  const sentimiento =
    senRaw === "positivo" || senRaw === "negativo" || senRaw === "neutro"
      ? senRaw
      : undefined;

  const topico_slug =
    typeof raw.topico_slug === "string" && raw.topico_slug.length > 0
      ? raw.topico_slug
      : undefined;

  const urlDesde = parseIsoDateParam(raw.fecha_desde);
  const urlHasta = parseIsoDateParam(raw.fecha_hasta);
  const defaults = defaultReviewDateRange();
  let fecha_desde = defaults.fecha_desde;
  let fecha_hasta = defaults.fecha_hasta;
  if (urlDesde && urlHasta && urlDesde <= urlHasta) {
    fecha_desde = urlDesde;
    fecha_hasta = urlHasta;
  }

  const query: ReviewsExplorerQuery = {
    fecha_desde,
    fecha_hasta,
  };
  if (page > 1) query.page = String(page);
  if (sentimiento) query.sentimiento = sentimiento;
  if (topico_slug) query.topico_slug = topico_slug;

  return { page, sentimiento, topico_slug, fecha_desde, fecha_hasta, query };
}

export default async function ReviewsExplorerPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const { page, sentimiento, topico_slug, fecha_desde, fecha_hasta, query } =
    parseSearchParams(raw);

  const hotelId = getReviewsExplorerHotelId();
  const dateRangeLabel = formatReviewDateRangeLabel(fecha_desde, fecha_hasta);

  const envelope = await fetchDashboardReviews({
    hotel_id: hotelId,
    fecha_desde,
    fecha_hasta,
    sentimiento,
    topico_slug,
    page,
    page_size: 20,
    orden: "fecha_desc",
  });

  if (!envelope.ok || !envelope.data) {
    const msg =
      envelope.error?.mensaje ??
      "No se pudo cargar el listado de reseñas. Comprueba que la API del dashboard esté en ejecución y que `NEXT_PUBLIC_DASHBOARD_API_URL` apunte al servidor correcto.";
    return (
      <div className="mx-auto max-w-[1400px] p-8 pb-12 lg:p-12">
        <div className="border-error/30 bg-error-container/10 rounded-xl border p-8">
          <h2 className="font-headline text-error mb-2 text-xl font-bold">
            Error al cargar reseñas
          </h2>
          <p className="font-body text-on-surface/80">{msg}</p>
          {envelope.error?.codigo ? (
            <p className="font-label text-on-surface/50 mt-4 text-xs">
              Código: {envelope.error.codigo}
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  const { items: rawItems, paginacion } = envelope.data;
  const items = rawItems.map(mapReviewListItemToExplorer);

  const filterBar: ReviewsFilterBarData = {
    dateRangeLabel,
    sentimentChips: [
      {
        id: "all",
        label: "Todos",
        style: "all",
        value: null,
      },
      {
        id: "pos",
        label: "Positivo",
        style: "positive",
        value: "positivo",
      },
      {
        id: "neu",
        label: "Neutro",
        style: "neutral",
        value: "neutro",
      },
      {
        id: "crit",
        label: "Negativo",
        style: "critical",
        value: "negativo",
      },
    ],
    themeTags: buildThemeTagsFromItems(rawItems, topico_slug),
  };

  return (
    <div className="mx-auto max-w-[1400px] p-8 pb-12 lg:p-12">
      <ReviewsExplorerView
        header={header}
        filterBar={filterBar}
        query={query}
        items={items}
        paginacion={paginacion}
      />
    </div>
  );
}
