export type DashboardPeriod = "month" | "quarter" | "semester";

/** Mes calendario (1–12) para consultas al DashboardBackend. */
export type YearMonth = { anio: number; mes: number };

function addMonths(y: number, m: number, delta: number): YearMonth {
  const d = new Date(y, m - 1 + delta, 1);
  return { anio: d.getFullYear(), mes: d.getMonth() + 1 };
}

/** Último mes civil ya cerrado (respecto a la fecha actual del cliente). */
export function getLastClosedMonth(): YearMonth {
  const now = new Date();
  const d = new Date(now.getFullYear(), now.getMonth(), 1);
  d.setMonth(d.getMonth() - 1);
  return { anio: d.getFullYear(), mes: d.getMonth() + 1 };
}

/**
 * Ventana de meses para el hero: 1, 3 o 6 meses consecutivos terminando en el último mes cerrado.
 */
export function getHeroMonthWindow(period: DashboardPeriod): YearMonth[] {
  const end = getLastClosedMonth();
  const count =
    period === "month" ? 1 : period === "quarter" ? 3 : 6;
  const result: YearMonth[] = [];
  for (let j = 0; j < count; j++) {
    const offset = -(count - 1 - j);
    result.push(addMonths(end.anio, end.mes, offset));
  }
  return result;
}
