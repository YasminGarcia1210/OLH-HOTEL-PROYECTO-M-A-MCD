import Link from "next/link";

import type { ReviewsFilterBarData } from "@/lib/reviews-types";
import {
  buildReviewsExplorerUrl,
  type ReviewsExplorerQuery,
} from "@/lib/reviews-url";

import { isMoreThemesSlug } from "@/lib/reviews-theme-tags";

import { ReviewsDateRangePicker } from "./ReviewsDateRangePicker";

type Props = {
  data: ReviewsFilterBarData;
  query: ReviewsExplorerQuery;
};

export function ReviewsFilterBar({ data, query }: Props) {
  return (
    <section className="bg-surface-container mb-8 flex flex-col gap-6 rounded-xl p-6 shadow-sm">
      <div className="w-full min-w-0">
        <label className="font-label mb-2 block text-[10px] font-bold uppercase tracking-widest text-gold-bright">
          Rango de fechas
        </label>
        <div className="focus-within:border-gold-bright flex min-w-0 flex-col gap-3 rounded border-b-2 border-transparent bg-surface-container-low px-3 py-2.5 transition-all sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <div className="flex min-w-0 shrink items-center gap-2">
            <span className="material-symbols-outlined shrink-0 text-sm text-on-surface/40">
              calendar_today
            </span>
            <span className="text-sm text-on-surface/80">{data.dateRangeLabel}</span>
          </div>
          <ReviewsDateRangePicker query={query} />
        </div>
      </div>
      <div className="flex min-w-0 flex-col gap-6 sm:flex-row sm:flex-wrap sm:items-start">
        <div className="min-w-0 flex-1 sm:min-w-[240px]">
          <label className="font-label mb-2 block text-[10px] font-bold uppercase tracking-widest text-gold-bright">
            Sentimiento
          </label>
          <div className="flex gap-2">
            {data.sentimentChips.map((chip) => {
              const value = chip.value;
              const hasSentimentFilter =
                query.sentimiento === "positivo" ||
                query.sentimiento === "negativo" ||
                query.sentimiento === "neutro";
              const active =
                value == null
                  ? !hasSentimentFilter
                  : query.sentimiento === value;
              const href =
                value == null
                  ? buildReviewsExplorerUrl(query, { page: 1, sentimiento: null })
                  : buildReviewsExplorerUrl(query, {
                      page: 1,
                      sentimiento: active ? null : value,
                    });

              if (chip.style === "all") {
                return (
                  <Link
                    key={chip.id}
                    href={href}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold transition-colors ${
                      active
                        ? "border-gold-bright bg-gold-bright/15 text-gold-bright"
                        : "border-gold-bright/25 bg-surface-container-highest text-on-surface/70 hover:border-gold-bright/40 hover:bg-surface-container-high"
                    }`}
                  >
                    <span className="bg-gold-bright/60 size-1.5 rounded-full" />
                    {chip.label}
                  </Link>
                );
              }
              if (chip.style === "positive") {
                return (
                  <Link
                    key={chip.id}
                    href={href}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold transition-colors ${
                      active
                        ? "border-tertiary bg-tertiary-container/30 text-tertiary"
                        : "border-tertiary-container/30 bg-tertiary-container/10 text-tertiary hover:bg-tertiary-container/20"
                    }`}
                  >
                    <span className="bg-tertiary size-1.5 rounded-full" />
                    {chip.label}
                  </Link>
                );
              }
              if (chip.style === "neutral") {
                return (
                  <Link
                    key={chip.id}
                    href={href}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold transition-colors ${
                      active
                        ? "border-on-surface/30 bg-on-surface/15 text-on-surface"
                        : "border-on-surface/10 bg-on-surface/5 text-on-surface/60 hover:bg-on-surface/10"
                    }`}
                  >
                    <span className="size-1.5 rounded-full bg-white/20" />
                    {chip.label}
                  </Link>
                );
              }
              return (
                <Link
                  key={chip.id}
                  href={href}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold transition-colors ${
                    active
                      ? "border-error bg-error-container/40 text-error"
                      : "border-error-container/40 bg-error-container/20 text-error hover:bg-error-container/30"
                  }`}
                >
                  <span className="bg-error size-1.5 rounded-full" />
                  {chip.label}
                </Link>
              );
            })}
          </div>
        </div>
        <div className="min-w-0 flex-[1.5] sm:min-w-[300px]">
          <label className="font-label mb-2 block text-[10px] font-bold uppercase tracking-widest text-gold-bright">
            Tópicos
          </label>
          <div className="flex flex-wrap gap-2">
            {data.themeTags.map((tag) => {
              if (isMoreThemesSlug(tag.slug)) {
                return (
                  <span
                    key={tag.slug}
                    className="border-primary/20 bg-primary-container/20 text-primary whitespace-nowrap rounded border px-3 py-1.5 text-xs"
                  >
                    {tag.label}
                  </span>
                );
              }
              const active = tag.active === true;
              const href = buildReviewsExplorerUrl(query, {
                page: 1,
                topico_slug: active ? null : tag.slug,
              });
              return (
                <Link
                  key={tag.slug}
                  href={href}
                  className={`whitespace-nowrap rounded px-3 py-1.5 text-xs transition-colors ${
                    active
                      ? "border-primary bg-primary-container/30 text-primary border font-bold"
                      : "bg-surface-container-highest text-on-surface/80 hover:bg-surface-container-high"
                  }`}
                >
                  {tag.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
