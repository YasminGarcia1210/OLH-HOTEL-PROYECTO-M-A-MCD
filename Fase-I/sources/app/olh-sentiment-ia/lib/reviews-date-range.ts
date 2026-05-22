/** Valida YYYY-MM-DD (calendario gregoriano). */
export function parseIsoDateParam(
  raw: string | string[] | undefined,
): string | undefined {
  const s = typeof raw === "string" ? raw.trim() : undefined;
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return undefined;
  const [y, m, d] = s.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  if (
    dt.getFullYear() !== y ||
    dt.getMonth() !== m - 1 ||
    dt.getDate() !== d
  ) {
    return undefined;
  }
  return s;
}

export function formatReviewDateRangeLabel(
  fecha_desde: string,
  fecha_hasta: string,
): string {
  const fmt = (iso: string) => {
    const [y, m, day] = iso.split("-").map(Number);
    const d = new Date(y, m - 1, day);
    return d.toLocaleDateString("es-CO", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };
  return `${fmt(fecha_desde)} – ${fmt(fecha_hasta)}`;
}

/** Rango por defecto alineado con el backend (últimos 30 días hasta hoy). */

export function defaultReviewDateRange(): {
  fecha_desde: string;
  fecha_hasta: string;
  label: string;
} {
  const hasta = new Date();
  const desde = new Date(hasta);
  desde.setDate(desde.getDate() - 30);

  const pad = (n: number) => String(n).padStart(2, "0");
  const toIsoDate = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  const fecha_desde = toIsoDate(desde);
  const fecha_hasta = toIsoDate(hasta);

  return {
    fecha_desde,
    fecha_hasta,
    label: formatReviewDateRangeLabel(fecha_desde, fecha_hasta),
  };
}
