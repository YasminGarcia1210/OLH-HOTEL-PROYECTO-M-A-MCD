import type { HeroKpis } from "@/lib/mock-data";
import { SectionDivider } from "./SectionDivider";

type Props = {
  data: HeroKpis | null;
  loading?: boolean;
};

function HeroKpisSkeleton() {
  return (
    <div
      className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-2 lg:grid-cols-12"
      aria-busy
    >
      <div className="from-[#121A2A] via-[#0D1117] to-[#15111D] border-primary/20 relative col-span-1 flex min-h-[280px] flex-col justify-center overflow-hidden rounded-card border bg-gradient-to-br p-8 lg:col-span-5">
        <div className="bg-on-surface-variant/15 mb-4 h-3 w-32 rounded" />
        <div className="bg-on-surface-variant/15 mb-4 h-16 w-40 rounded" />
        <div className="bg-on-surface-variant/15 mb-6 h-4 w-full max-w-xs rounded" />
        <div className="bg-on-surface-variant/15 h-8 w-48 rounded-full" />
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 sm:grid-cols-3 lg:col-span-7">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="bg-surface-container rounded-card flex min-h-[160px] flex-col justify-center border border-white/5 p-6"
          >
            <div className="bg-on-surface-variant/15 mb-3 h-2 w-20 rounded" />
            <div className="bg-on-surface-variant/15 mb-3 h-10 w-24 rounded" />
            <div className="bg-on-surface-variant/15 h-2 w-full rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function HeroKpisSection({ data, loading = false }: Props) {
  return (
    <section>
      <SectionDivider label="✦ Sentimiento General · Core del Modelo" />
      {loading ? (
        <div className="animate-pulse opacity-70">
          <HeroKpisSkeleton />
        </div>
      ) : data == null ? (
        <div
          className="text-on-surface-variant/70 font-body bg-surface-container rounded-card border border-white/5 px-6 py-12 text-center text-sm"
          role="status"
        >
          No hay KPIs disponibles. Comprueba la conexión con el servidor o
          inténtalo de nuevo más tarde.
        </div>
      ) : (
        <div
          className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-2 lg:grid-cols-12"
          aria-busy={false}
        >
          <div className="from-[#121A2A] via-[#0D1117] to-[#15111D] border-primary/20 relative col-span-1 flex min-h-0 flex-col justify-center overflow-hidden rounded-card border bg-gradient-to-br p-8 lg:col-span-5">
            <div className="bg-primary/10 pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full blur-3xl" />
            <span className="text-on-surface-variant text-[11px] uppercase tracking-[1.5px] opacity-60">
              {data.sentimentLabel}
            </span>
            <div className="mt-4 flex items-baseline gap-2">
              <span className="font-headline text-primary text-7xl font-extrabold tracking-tighter">
                {data.sentimentScore}%
              </span>
            </div>
            <p className="text-on-surface-variant mt-2 text-sm">
              {data.sentimentSubtext}
            </p>
            <div className="mt-4 flex">
              <span className="border-tertiary/20 bg-tertiary/10 text-tertiary flex items-center gap-1.5 rounded-full border px-3.5 py-1 text-xs font-semibold">
                {data.deltaBadgeText}
              </span>
            </div>
          </div>
          <div className="flex min-h-0 flex-col md:h-full lg:col-span-7">
            <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 sm:grid-cols-3 sm:items-stretch">
              <div className="bg-surface-container rounded-card flex min-h-0 h-full flex-col justify-center border border-white/5 p-6">
                <span className="text-on-surface-variant/40 mb-2 text-[10px] uppercase tracking-widest">
                  {data.variationCard.label}
                </span>
                <span className="font-headline text-tertiary text-4xl font-bold">
                  {data.variationCard.value}
                </span>
                <p className="text-on-surface-variant/60 mt-2 text-[11px] leading-relaxed whitespace-pre-line">
                  {data.variationCard.subtext}
                </p>
              </div>
              <div className="bg-surface-container rounded-card flex min-h-0 h-full flex-col justify-center border border-white/5 p-6">
                <span className="text-on-surface-variant/40 mb-2 text-[10px] uppercase tracking-widest">
                  {data.bestArea.label}
                </span>
                <span className="font-headline text-tertiary text-4xl font-bold">
                  {data.bestArea.score}%
                </span>
                <p className="text-on-surface-variant/60 mt-2 text-[11px] leading-relaxed">
                  {data.bestArea.subtext}
                </p>
              </div>
              <div className="bg-surface-container rounded-card flex min-h-0 h-full flex-col justify-center border border-white/5 p-6">
                <span className="text-on-surface-variant/40 mb-2 text-[10px] uppercase tracking-widest">
                  {data.worstArea.label}
                </span>
                <span className="font-headline text-error text-4xl font-bold">
                  {data.worstArea.score}%
                </span>
                <p className="text-on-surface-variant/60 mt-2 text-[11px] leading-relaxed">
                  {data.worstArea.subtext}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
