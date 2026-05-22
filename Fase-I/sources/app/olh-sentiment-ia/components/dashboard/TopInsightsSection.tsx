import type { InsightRank } from "@/lib/mock-data";
import { SectionDivider } from "./SectionDivider";

type Props = {
  strengths: InsightRank[];
  painPoints: InsightRank[];
  loading?: boolean;
};

function pillClass(kind: InsightRank["pillClass"]) {
  if (kind === "tertiary") return "bg-tertiary/10 text-tertiary";
  if (kind === "error") return "bg-error/10 text-error";
  return "bg-warn-orange/10 text-warn-orange";
}

function InsightListSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="flex animate-pulse items-center justify-between gap-3"
        >
          <div className="flex flex-1 items-center gap-3">
            <div className="bg-on-surface-variant/15 h-3 w-4 rounded" />
            <div className="bg-on-surface-variant/15 h-3 flex-1 max-w-[180px] rounded" />
          </div>
          <div className="bg-on-surface-variant/15 h-7 w-14 shrink-0 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function TopInsightsSection({
  strengths,
  painPoints,
  loading = false,
}: Props) {
  return (
    <section>
      <SectionDivider label="🏆 Top Insights · Fortalezas vs. Pain Points" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="bg-surface-container rounded-card border border-white/5 p-6 shadow-[0px_12px_32px_rgba(225,226,237,0.04)]">
          <h3 className="font-body mb-6 flex items-center gap-2 text-sm font-bold">
            <span className="text-tertiary">◆</span> Top Fortalezas
          </h3>
          {loading ? (
            <InsightListSkeleton />
          ) : strengths.length === 0 ? (
            <p className="text-on-surface-variant/70 font-body text-sm">
              Sin tópicos con menciones en el mes de referencia.
            </p>
          ) : (
            <ul className="space-y-4">
              {strengths.map((row) => (
                <li
                  key={`${row.rank}-${row.name}`}
                  className="bg-surface-container-low/80 flex items-center justify-between gap-3 rounded-lg px-3 py-3"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="font-label text-on-surface-variant/40 w-4 shrink-0 text-[11px] font-bold">
                      {row.rank}
                    </span>
                    <span className="font-body truncate text-sm">{row.name}</span>
                  </div>
                  <span
                    className={`font-label shrink-0 rounded-full px-3 py-1 text-xs font-bold ${pillClass(row.pillClass)}`}
                  >
                    {row.score}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="bg-surface-container rounded-card border border-white/5 p-6 shadow-[0px_12px_32px_rgba(225,226,237,0.04)]">
          <h3 className="font-body mb-6 flex items-center gap-2 text-sm font-bold">
            <span className="text-error">◆</span> Top Pain Points
          </h3>
          {loading ? (
            <InsightListSkeleton />
          ) : painPoints.length === 0 ? (
            <p className="text-on-surface-variant/70 font-body text-sm">
              Sin pain points críticos registrados para este período.
            </p>
          ) : (
            <ul className="space-y-4">
              {painPoints.map((row) => (
                <li
                  key={`${row.rank}-${row.name}`}
                  className="bg-surface-container-low/80 flex items-center justify-between gap-3 rounded-lg px-3 py-3"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="font-label text-on-surface-variant/40 w-4 shrink-0 text-[11px] font-bold">
                      {row.rank}
                    </span>
                    <span className="font-body truncate text-sm">{row.name}</span>
                  </div>
                  <span
                    className={`font-label shrink-0 rounded-full px-3 py-1 text-xs font-bold ${pillClass(row.pillClass)}`}
                  >
                    {row.score}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
