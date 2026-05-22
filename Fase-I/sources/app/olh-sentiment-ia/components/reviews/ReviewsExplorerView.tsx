import Link from "next/link";

import type {
  ReviewExplorerItem,
  ReviewsFilterBarData,
  ReviewsPageHeader,
} from "@/lib/reviews-types";
import type { Paginacion } from "@/lib/reviews-api";
import { buildReviewsExplorerUrl, type ReviewsExplorerQuery } from "@/lib/reviews-url";

import { ReviewCard } from "./ReviewCard";
import { ReviewsFilterBar } from "./ReviewsFilterBar";

type Props = {
  header: ReviewsPageHeader;
  filterBar: ReviewsFilterBarData;
  query: ReviewsExplorerQuery;
  items: ReviewExplorerItem[];
  paginacion: Paginacion;
};

export function ReviewsExplorerView({
  header,
  filterBar,
  query,
  items,
  paginacion,
}: Props) {
  const { page, total_pages } = paginacion;

  return (
    <div className="relative">
      <div className="mb-10 max-w-5xl">
        <h2 className="font-headline mb-2 text-4xl font-bold tracking-tight text-on-surface md:text-5xl">
          {header.title}
        </h2>
        <p className="font-body text-lg text-on-surface/60">{header.subtitle}</p>
      </div>
      <ReviewsFilterBar data={filterBar} query={query} />
      <div className="mx-auto max-w-6xl space-y-6">
        {items.length === 0 ? (
          <p className="font-body text-on-surface/50 py-12 text-center text-base">
            No hay reseñas para los filtros seleccionados.
          </p>
        ) : (
          items.map((item) => <ReviewCard key={item.id} item={item} />)
        )}
      </div>
      {total_pages > 1 ? (
        <nav
          className="mx-auto mt-12 flex max-w-6xl flex-wrap items-center justify-center gap-4"
          aria-label="Paginación"
        >
          {page > 1 ? (
            <Link
              href={buildReviewsExplorerUrl(query, { page: page - 1 })}
              className="text-gold-bright hover:bg-surface-container-highest rounded-lg px-4 py-2 text-sm font-bold transition-colors"
            >
              Anterior
            </Link>
          ) : (
            <span className="text-on-surface/25 cursor-not-allowed px-4 py-2 text-sm">
              Anterior
            </span>
          )}
          <span className="font-label text-on-surface/50 text-xs">
            Página {page} de {total_pages}
          </span>
          {page < total_pages ? (
            <Link
              href={buildReviewsExplorerUrl(query, { page: page + 1 })}
              className="text-gold-bright hover:bg-surface-container-highest rounded-lg px-4 py-2 text-sm font-bold transition-colors"
            >
              Siguiente
            </Link>
          ) : (
            <span className="text-on-surface/25 cursor-not-allowed px-4 py-2 text-sm">
              Siguiente
            </span>
          )}
        </nav>
      ) : null}
      <div
        className="pointer-events-none fixed bottom-12 right-12 size-64 rounded-full bg-tertiary/5 blur-[100px]"
        aria-hidden
      />
    </div>
  );
}
