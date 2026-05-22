import type { PainPointCard } from "@/lib/mock-data";
import { SectionDivider } from "./SectionDivider";

type Props = {
  items: PainPointCard[];
  loading?: boolean;
  /** Lista vacía procede de API (sin top5), no de error de carga. */
  emptyFromApi?: boolean;
  /** Fallo al cargar desde el servidor. */
  loadError?: boolean;
};

function cardShellClasses(tag: PainPointCard["tag"]) {
  if (tag === "crit") {
    return "border-error/20 bg-error/5 border-2";
  }
  if (tag === "warn") {
    return "border-warn-orange/25 bg-warn-orange/5 border-2";
  }
  return "border-surface-variant/10 border";
}

function scoreTextClass(tag: PainPointCard["tag"]) {
  if (tag === "crit") return "text-error";
  if (tag === "warn") return "text-warn-orange";
  return "text-secondary";
}

function deltaTextClass(tag: PainPointCard["tag"]) {
  if (tag === "crit") return "text-error";
  if (tag === "warn") return "text-warn-orange";
  return "text-tertiary";
}

function statusTag(tag: PainPointCard["tag"]) {
  if (tag === "crit") {
    return <span className="tag tag-crit">Crítico</span>;
  }
  if (tag === "warn") {
    return <span className="tag tag-warn">Atención</span>;
  }
  return <span className="tag tag-ok">Estable</span>;
}

function PainPointCardsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="bg-surface-container rounded-card border border-white/5 p-6 text-center shadow-[0px_12px_32px_rgba(225,226,237,0.04)]"
        >
          <div className="bg-on-surface-variant/15 mx-auto mb-3 h-8 w-8 rounded-full" />
          <div className="bg-on-surface-variant/15 mx-auto mb-2 h-2 w-24 rounded" />
          <div className="bg-on-surface-variant/15 mx-auto mb-2 h-10 w-20 rounded" />
          <div className="bg-on-surface-variant/15 mx-auto mb-4 h-2 w-16 rounded" />
          <div className="bg-on-surface-variant/15 mx-auto h-6 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function PainPointsIndexSection({
  items,
  loading = false,
  emptyFromApi = false,
  loadError = false,
}: Props) {
  return (
    <section>
      <SectionDivider label="⚠️ Pain Points Index · Tópicos Específicos" />
      {loading ? (
        <PainPointCardsSkeleton />
      ) : loadError ? (
        <p className="text-on-surface-variant/70 font-body bg-surface-container rounded-card border border-white/5 px-6 py-8 text-center text-sm shadow-[0px_12px_32px_rgba(225,226,237,0.04)]">
          No se pudieron cargar los pain points. Comprueba la conexión o
          inténtalo más tarde.
        </p>
      ) : emptyFromApi ? (
        <p className="text-on-surface-variant/70 font-body bg-surface-container rounded-card border border-white/5 px-6 py-8 text-center text-sm shadow-[0px_12px_32px_rgba(225,226,237,0.04)]">
          No hay pain points en el top mensual para el mes de referencia del
          período seleccionado.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((card) => {
            const box = cardShellClasses(card.tag);
            return (
              <div
                key={card.slug}
                className={`bg-surface-container rounded-card p-6 text-center shadow-[0px_12px_32px_rgba(225,226,237,0.04)] ${box}`}
              >
                <span className="mb-2 block text-2xl">{card.icon}</span>
                <span className="text-on-surface-variant/40 text-[10px] font-bold uppercase tracking-widest">
                  {card.name}
                </span>
                <div
                  className={`font-headline mt-2 text-4xl font-bold ${scoreTextClass(card.tag)}`}
                >
                  {card.score}%
                </div>
                <span
                  className={`mt-1 block text-xs font-bold ${deltaTextClass(card.tag)}`}
                >
                  {card.deltaLabel}
                </span>
                <div className="mt-4">{statusTag(card.tag)}</div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
