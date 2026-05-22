import type { ExecutiveKpi } from "@/lib/mock-data";
import { SectionDivider } from "./SectionDivider";

type Props = {
  items: ExecutiveKpi[];
  /** Mientras el hero / KPIs cargan desde el backend. */
  loading?: boolean;
};

function valueClass(c: ExecutiveKpi["valueClass"]) {
  if (c === "primary") return "text-primary";
  if (c === "tertiary") return "text-tertiary";
  return "text-error";
}

function ExecutiveSummarySkeleton() {
  return (
    <div className="grid grid-cols-2 gap-8 text-center md:grid-cols-3 lg:grid-cols-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i}>
          <div className="bg-on-surface-variant/15 mx-auto mb-3 h-2 w-16 rounded" />
          <div className="bg-on-surface-variant/15 mx-auto mb-2 h-8 w-14 rounded" />
          <div className="bg-on-surface-variant/15 mx-auto h-2 w-20 rounded" />
        </div>
      ))}
    </div>
  );
}

export function ExecutiveSummarySection({ items, loading = false }: Props) {
  return (
    <section>
      <SectionDivider label="Resumen Ejecutivo · Los 6 KPIs clave" />
      <div
        className="rounded-card border border-primary/20 bg-gradient-to-br from-surface-container-low via-background to-surface-container p-10 shadow-[0px_12px_32px_rgba(225,226,237,0.04)] transition-opacity duration-300 ease-in-out"
        aria-busy={loading}
      >
        <h3 className="font-headline text-primary mb-2 text-xl font-bold">
          Índice de experiencia del cliente (CEI)
        </h3>
        <p className="text-on-surface-variant/40 mb-10 font-body text-xs">
          Indicadores esenciales para presentación directiva (misma fuente que el
          bloque de sentimiento general).
        </p>
        {loading ? (
          <div className="animate-pulse opacity-70">
            <ExecutiveSummarySkeleton />
          </div>
        ) : items.length === 0 ? (
          <p
            className="text-on-surface-variant/70 font-body text-center text-sm"
            role="status"
          >
            No hay resumen ejecutivo disponible sin los KPIs del servidor.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-8 text-center md:grid-cols-3 lg:grid-cols-6">
            {items.map((kpi) => (
              <div key={kpi.label}>
                <p className="font-label text-on-surface-variant/40 mb-3 text-[10px] uppercase tracking-widest">
                  {kpi.label}
                </p>
                <span
                  className={`font-headline text-3xl font-bold ${valueClass(kpi.valueClass)}`}
                >
                  {kpi.value}
                </span>
                <p className="font-body text-on-surface-variant/40 mt-2 text-[10px] leading-relaxed">
                  {kpi.subtext}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
