import type { CategoryScore } from "@/lib/mock-data";
import { SectionDivider } from "./SectionDivider";

type Props = {
  items: CategoryScore[];
  loading?: boolean;
};

function CategoryGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="bg-surface-container rounded-card-sm border border-white/5 p-5"
        >
          <div className="bg-on-surface-variant/15 mb-3 h-6 w-6 rounded" />
          <div className="bg-on-surface-variant/15 mb-3 h-2 w-20 rounded" />
          <div className="bg-on-surface-variant/15 mb-3 h-8 w-14 rounded" />
          <div className="bg-on-surface-variant/10 mb-2 h-1 w-full rounded-full" />
          <div className="bg-on-surface-variant/15 h-2 w-16 rounded" />
        </div>
      ))}
    </div>
  );
}

export function CategoryGrid({ items, loading = false }: Props) {
  return (
    <section>
      <SectionDivider label="🧩 Score por Categoría · Desglose Completo" />
      {loading ? (
        <div className="animate-pulse opacity-70">
          <CategoryGridSkeleton />
        </div>
      ) : items.length === 0 ? (
        <p
          className="text-on-surface-variant/70 font-body bg-surface-container rounded-card border border-white/5 px-6 py-8 text-center text-sm"
          role="status"
        >
          Sin datos de categorías para mostrar.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {items.map((cat) => {
            const base =
              "bg-surface-container rounded-card-sm border border-white/5 p-5 transition-transform hover:-translate-y-0.5";
            const highlight =
              cat.highlight === "error-border"
                ? "border-error/30 border-2 bg-error/5"
                : "";
            return (
              <div key={cat.name} className={`${base} ${highlight}`}>
                <span className="mb-2 block text-lg">{cat.icon}</span>
                <p className="text-on-surface-variant/60 mb-2 text-[11px] font-medium">
                  {cat.name}
                </p>
                <span
                  className={`font-headline text-3xl font-bold ${cat.scoreTextClass}`}
                >
                  {cat.score}%
                </span>
                <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/5">
                  <div
                    className={`h-full ${cat.barColorClass}`}
                    style={{ width: `${cat.score}%` }}
                  />
                </div>
                <span
                  className={`mt-2 block text-[10px] font-bold ${cat.deltaTextClass}`}
                >
                  {cat.deltaLabel}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
