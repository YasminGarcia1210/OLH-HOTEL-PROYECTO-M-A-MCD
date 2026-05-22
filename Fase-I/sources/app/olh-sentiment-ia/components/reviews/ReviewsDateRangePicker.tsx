"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { buildReviewsExplorerUrl } from "@/lib/reviews-url";
import type { ReviewsExplorerQuery } from "@/lib/reviews-url";

type Props = {
  query: ReviewsExplorerQuery;
};

export function ReviewsDateRangePicker({ query }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function navigate(patch: Parameters<typeof buildReviewsExplorerUrl>[1]) {
    const href = buildReviewsExplorerUrl(query, patch);
    startTransition(() => {
      router.push(href);
    });
  }

  function onDesdeChange(e: React.ChangeEvent<HTMLInputElement>) {
    const nextDesde = e.target.value;
    if (!nextDesde) return;
    let nextHasta = query.fecha_hasta;
    if (nextDesde > nextHasta) {
      nextHasta = nextDesde;
    }
    navigate({ fecha_desde: nextDesde, fecha_hasta: nextHasta, page: 1 });
  }

  function onHastaChange(e: React.ChangeEvent<HTMLInputElement>) {
    const nextHasta = e.target.value;
    if (!nextHasta) return;
    let nextDesde = query.fecha_desde;
    if (nextDesde > nextHasta) {
      nextDesde = nextHasta;
    }
    navigate({ fecha_desde: nextDesde, fecha_hasta: nextHasta, page: 1 });
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <span className="font-label mb-1 block text-[9px] uppercase tracking-wider text-on-surface/50">
          Desde
        </span>
        <input
          type="date"
          value={query.fecha_desde}
          onChange={onDesdeChange}
          disabled={pending}
          className="border-gold-bright/30 bg-surface-container-low text-on-surface focus:border-gold-bright focus:ring-gold-bright/20 rounded-lg border px-2 py-2 text-sm outline-none focus:ring-2 disabled:opacity-50"
          aria-label="Fecha desde"
        />
      </div>
      <div>
        <span className="font-label mb-1 block text-[9px] uppercase tracking-wider text-on-surface/50">
          Hasta
        </span>
        <input
          type="date"
          value={query.fecha_hasta}
          onChange={onHastaChange}
          disabled={pending}
          className="border-gold-bright/30 bg-surface-container-low text-on-surface focus:border-gold-bright focus:ring-gold-bright/20 rounded-lg border px-2 py-2 text-sm outline-none focus:ring-2 disabled:opacity-50"
          aria-label="Fecha hasta"
        />
      </div>
    </div>
  );
}
