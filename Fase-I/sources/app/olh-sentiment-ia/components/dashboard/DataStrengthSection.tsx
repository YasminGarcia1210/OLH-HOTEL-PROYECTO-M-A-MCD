import type { DataStrength } from "@/lib/mock-data";
import { SectionDivider } from "./SectionDivider";
import { SparklineBars } from "./SparklineBars";

type Props = {
  data: DataStrength | null;
  loading?: boolean;
};

function DataStrengthSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="border-surface-variant/10 bg-surface-container rounded-card border p-6"
        >
          <div className="bg-on-surface-variant/15 mx-auto mb-3 h-2 w-24 rounded" />
          <div className="bg-on-surface-variant/15 mx-auto mb-2 h-10 w-20 rounded" />
          <div className="bg-on-surface-variant/15 mx-auto h-2 w-32 rounded" />
        </div>
      ))}
    </div>
  );
}

export function DataStrengthSection({ data, loading = false }: Props) {
  return (
    <section>
      <SectionDivider label="📊 Data Strength · Volumen y Confiabilidad" />
      {loading ? (
        <div className="animate-pulse opacity-70">
          <DataStrengthSkeleton />
        </div>
      ) : data == null ? (
        <p
          className="text-on-surface-variant/70 font-body bg-surface-container rounded-card border border-white/5 px-6 py-8 text-center text-sm"
          role="status"
        >
          No hay datos de volumen y confiabilidad disponibles.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border-surface-variant/10 bg-surface-container rounded-card border p-6 text-center">
            <span className="text-on-surface-variant/40 text-[10px] uppercase tracking-widest">
              Reviews Analizadas
            </span>
            <div className="font-headline text-on-background mt-2 text-3xl font-bold">
              {data.reviewsTotal.toLocaleString("es-CO")}
            </div>
            <span className="text-on-surface-variant/40 mt-1 block text-[10px]">
              {data.reviewsTotalLabel}
            </span>
          </div>
          <div className="border-surface-variant/10 bg-surface-container rounded-card border p-6 text-center">
            <span className="text-on-surface-variant/40 text-[10px] uppercase tracking-widest">
              Reviews / Mes
            </span>
            <div className="font-headline text-on-background mt-2 text-3xl font-bold">
              {data.reviewsPerMonth}
            </div>
            <span className="text-on-surface-variant/40 mt-1 block text-[10px]">
              {data.reviewsPerMonthLabel}
            </span>
            <SparklineBars values={data.sparklineValues} />
          </div>
          <div className="border-surface-variant/10 bg-surface-container rounded-card border p-6 text-center">
            <span className="text-on-surface-variant/40 text-[10px] uppercase tracking-widest">
              Fuentes de Datos
            </span>
            <div className="font-headline text-secondary mt-2 text-3xl font-bold">
              {data.sourceCount}
            </div>
            <span className="text-on-surface-variant/40 mt-1 block text-[10px]">
              {data.sourcesLabel}
            </span>
          </div>
          <div className="border-surface-variant/10 bg-surface-container rounded-card border p-6 text-center">
            <span className="text-on-surface-variant/40 text-[10px] uppercase tracking-widest">
              {data.reliabilityLabel}
            </span>
            <div className="font-headline text-tertiary mt-2 text-3xl font-bold">
              {data.reliabilityValue}
            </div>
            <span className="text-on-surface-variant/40 mt-1 block text-[10px]">
              {data.reliabilitySubtext}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
