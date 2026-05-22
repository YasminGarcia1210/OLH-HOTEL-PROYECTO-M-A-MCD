import type { AdvancedMetricsBlock } from "@/lib/mock-data";
import { SectionDivider } from "./SectionDivider";

type Props = {
  data: AdvancedMetricsBlock;
};

export function AdvancedMetricsSection({ data }: Props) {
  return (
    <section className="pb-12 hidden">
      <SectionDivider label="🚀 Métricas Avanzadas · Data Science" />
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {data.row1.map((m) => (
            <div
              key={m.label}
              className="border-surface-variant/10 bg-surface-container rounded-card border p-6 text-center"
            >
              <span className="text-on-surface-variant/40 text-[10px] uppercase tracking-widest">
                {m.label}
              </span>
              <div
                className={`font-headline mt-2 text-4xl font-bold ${m.valueClass}`}
              >
                {m.value}
              </div>
              <p className="text-on-surface-variant/40 mt-3 text-[11px] leading-relaxed">
                {m.description}
              </p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {data.row2.map((m) => (
            <div
              key={m.label}
              className="border-surface-variant/10 bg-surface-container rounded-card border p-6 text-center"
            >
              <span className="text-on-surface-variant/40 text-[10px] uppercase tracking-widest">
                {m.label}
              </span>
              <div
                className={`font-headline mt-2 text-4xl font-bold ${m.valueClass}`}
              >
                {m.value}
              </div>
              <p className="text-on-surface-variant/40 mt-3 text-[11px] leading-relaxed">
                {m.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
