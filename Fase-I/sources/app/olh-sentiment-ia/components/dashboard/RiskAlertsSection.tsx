import type { RiskAlerts } from "@/lib/mock-data";
import { SectionDivider } from "./SectionDivider";
import { RiskDonut } from "./RiskDonut";

type Props = {
  data: RiskAlerts | null;
  loading?: boolean;
};

function Dot({ variant }: { variant: "error" | "warn-orange" }) {
  const cls =
    variant === "error" ? "bg-error" : "bg-warn-orange";
  return <span className={`h-2 w-2 shrink-0 rounded-full ${cls}`} />;
}

function RiskAlertsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <div className="border-surface-variant/10 bg-surface-container rounded-card h-full border p-8 lg:col-span-8">
        <div className="mb-8 grid grid-cols-3 gap-8">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="text-center">
              <div className="bg-on-surface-variant/15 mx-auto mb-2 h-2 w-20 rounded" />
              <div className="bg-on-surface-variant/15 mx-auto h-8 w-12 rounded" />
            </div>
          ))}
        </div>
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-on-surface-variant/10 h-10 rounded" />
          ))}
        </div>
      </div>
      <div className="bg-on-surface-variant/10 flex min-h-[200px] items-center justify-center rounded-card lg:col-span-4">
        <div className="bg-on-surface-variant/15 h-40 w-40 rounded-full" />
      </div>
    </div>
  );
}

export function RiskAlertsSection({ data, loading = false }: Props) {
  const sectionLabel = data?.sectionLabel ?? "Riesgo Reputacional · Alertas";

  return (
    <section>
      <SectionDivider label={sectionLabel} />
      {loading ? (
        <div className="animate-pulse opacity-70">
          <RiskAlertsSkeleton />
        </div>
      ) : data == null ? (
        <p
          className="text-on-surface-variant/70 font-body bg-surface-container rounded-card border border-white/5 px-6 py-8 text-center text-sm"
          role="status"
        >
          No hay datos de riesgo reputacional disponibles.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="border-surface-variant/10 bg-surface-container rounded-card h-full border p-8 lg:col-span-8">
            <div className="mb-8 grid grid-cols-3 gap-8 text-center">
              <div>
                <p className="text-on-surface-variant/40 mb-1 text-[10px] uppercase tracking-widest">
                  Tópicos en Alerta
                </p>
                <span className="font-headline text-error text-3xl font-bold">
                  {data.summary.topicsInAlert}
                </span>
              </div>
              <div>
                <p className="text-on-surface-variant/40 mb-1 text-[10px] uppercase tracking-widest">
                  % Críticos
                </p>
                <span className="font-headline text-warn-orange text-3xl font-bold">
                  {data.summary.criticalPercent}%
                </span>
              </div>
              <div>
                <p className="text-on-surface-variant/40 mb-1 text-[10px] uppercase tracking-widest">
                  Nuevas (7d)
                </p>
                <span className="font-headline text-primary text-3xl font-bold">
                  {data.summary.newIn7d}
                </span>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-surface-variant/10 text-on-surface-variant/40 border-b text-left text-[10px] uppercase tracking-widest">
                    <th className="pb-3">Tópico</th>
                    <th className="pb-3">Score</th>
                    <th className="pb-3">Estado</th>
                    <th className="pb-3">Tendencia</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {data.tableRows.map((row) => (
                    <tr
                      key={row.topic}
                      className="border-surface-variant/10 border-b last:border-0"
                    >
                      <td className="py-4">
                        <div className="flex items-center gap-2">
                          <Dot variant={row.dotClass} />
                          {row.topic}
                        </div>
                      </td>
                      <td className="text-on-surface-variant py-4 font-bold">
                        {row.score}%
                      </td>
                      <td className="py-4">
                        <span
                          className={
                            row.status === "crit" ? "tag tag-crit" : "tag tag-warn"
                          }
                        >
                          {row.status === "crit" ? "Crítico" : "Alerta"}
                        </span>
                      </td>
                      <td className="text-error py-4 text-xs font-bold">
                        {row.trendLabel}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="flex lg:col-span-4">
            <RiskDonut
              centerPercent={data.donut.centerPercent}
              centerSubtext={data.donut.centerSubtext}
              caption={data.donut.caption}
            />
          </div>
        </div>
      )}
    </section>
  );
}
