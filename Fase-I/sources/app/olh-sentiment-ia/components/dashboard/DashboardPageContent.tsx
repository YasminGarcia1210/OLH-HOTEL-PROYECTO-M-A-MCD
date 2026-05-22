"use client";

import { useEffect, useState } from "react";

import { AdvancedMetricsSection } from "@/components/dashboard/AdvancedMetricsSection";
import { CategoryGrid } from "@/components/dashboard/CategoryGrid";
import { DashboardCanvasFooter } from "@/components/dashboard/DashboardCanvasFooter";
import { DataStrengthSection } from "@/components/dashboard/DataStrengthSection";
import { ExecutiveSummarySection } from "@/components/dashboard/ExecutiveSummarySection";
import { HeroKpisSection } from "@/components/dashboard/HeroKpisSection";
import { PainPointsIndexSection } from "@/components/dashboard/PainPointsIndexSection";
import { RiskAlertsSection } from "@/components/dashboard/RiskAlertsSection";
import { SectionDivider } from "@/components/dashboard/SectionDivider";
import { TopInsightsSection } from "@/components/dashboard/TopInsightsSection";
import { TrendChart } from "@/components/dashboard/TrendChart";
import {
  buildCategoryScoresFromMetricas,
  fetchDataStrengthForPeriod,
  fetchHeroKpisForPeriod,
  fetchMetricasTopicos,
  fetchPainPointsIndexForPeriod,
  fetchRiskAlertsForPeriod,
  fetchTopInsightsForPeriod,
  fetchTrendSeriesForPeriod,
} from "@/lib/dashboard-metricas-api";
import {
  type DashboardPeriod,
  getHeroMonthWindow,
} from "@/lib/dashboard-period";
import {
  advancedMetrics,
  dashboardFooterNote,
  type CategoryScore,
  type DataStrength,
  type ExecutiveKpi,
  type HeroKpis,
  type InsightRank,
  type PainPointCard,
  type RiskAlerts,
  type TrendSeries,
} from "@/lib/mock-data";
import { getReviewsExplorerHotelId } from "@/lib/reviews-api";

const PERIOD_OPTIONS: { id: DashboardPeriod; label: string }[] = [
  { id: "month", label: "Último mes" },
  { id: "quarter", label: "Último trimestre" },
  { id: "semester", label: "Último semestre" },
];

type HeroApiState =
  | { status: "loading" }
  | { status: "ok"; data: HeroKpis; executiveKpis: ExecutiveKpi[] }
  | { status: "error"; message: string };

type TrendApiState = {
  loading: boolean;
  data: TrendSeries | null;
  errorMessage: string | null;
  isEmpty: boolean;
};

type DataStrengthApiState = {
  loading: boolean;
  data: DataStrength | null;
  errorMessage: string | null;
};

type RiskAlertsApiState = {
  loading: boolean;
  data: RiskAlerts | null;
  errorMessage: string | null;
};

type CategoryScoresApiState = {
  loading: boolean;
  items: CategoryScore[];
  errorMessage: string | null;
};

type TopInsightsApiState = {
  loading: boolean;
  strengths: InsightRank[];
  painPoints: InsightRank[];
  errorMessage: string | null;
};

type PainPointsIndexApiState = {
  loading: boolean;
  fromApi: boolean;
  items: PainPointCard[];
  errorMessage: string | null;
};

export function DashboardPageContent() {
  const [period, setPeriod] = useState<DashboardPeriod>("semester");
  const [heroApi, setHeroApi] = useState<HeroApiState>({ status: "loading" });
  const [trendApi, setTrendApi] = useState<TrendApiState>({
    loading: true,
    data: null,
    errorMessage: null,
    isEmpty: false,
  });
  const [dataStrengthApi, setDataStrengthApi] = useState<DataStrengthApiState>({
    loading: true,
    data: null,
    errorMessage: null,
  });
  const [riskAlertsApi, setRiskAlertsApi] = useState<RiskAlertsApiState>({
    loading: true,
    data: null,
    errorMessage: null,
  });
  const [categoryScoresApi, setCategoryScoresApi] =
    useState<CategoryScoresApiState>({
      loading: true,
      items: [],
      errorMessage: null,
    });
  const [topInsightsApi, setTopInsightsApi] = useState<TopInsightsApiState>({
    loading: true,
    strengths: [],
    painPoints: [],
    errorMessage: null,
  });
  const [painPointsIndexApi, setPainPointsIndexApi] =
    useState<PainPointsIndexApiState>({
      loading: true,
      fromApi: false,
      items: [],
      errorMessage: null,
    });

  useEffect(() => {
    let cancelled = false;
    const hotelId = getReviewsExplorerHotelId();
    fetchHeroKpisForPeriod(period, hotelId).then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setHeroApi({
          status: "ok",
          data: result.data,
          executiveKpis: result.executiveKpis,
        });
      } else {
        setHeroApi({ status: "error", message: result.error });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [period]);

  useEffect(() => {
    let cancelled = false;
    const hotelId = getReviewsExplorerHotelId();
    const monthWindow = getHeroMonthWindow(period);
    const anchor = monthWindow[monthWindow.length - 1];

    if (!anchor) {
      return () => {
        cancelled = true;
      };
    }

    fetchMetricasTopicos(hotelId, anchor.anio, anchor.mes).then((result) => {
      if (cancelled) return;
      if (!result.ok) {
        setCategoryScoresApi({
          loading: false,
          items: [],
          errorMessage:
            result.error?.mensaje ?? "No se pudieron cargar tópicos.",
        });
        return;
      }
      const mapped = buildCategoryScoresFromMetricas(result.data ?? []);
      setCategoryScoresApi({
        loading: false,
        items: mapped,
        errorMessage: null,
      });
    });

    return () => {
      cancelled = true;
    };
  }, [period]);

  useEffect(() => {
    let cancelled = false;
    const hotelId = getReviewsExplorerHotelId();
    fetchTopInsightsForPeriod(period, hotelId).then((result) => {
      if (cancelled) return;
      if (!result.ok) {
        setTopInsightsApi({
          loading: false,
          strengths: [],
          painPoints: [],
          errorMessage: result.error,
        });
        return;
      }
      setTopInsightsApi({
        loading: false,
        strengths: result.data.strengths,
        painPoints: result.data.painPoints,
        errorMessage: null,
      });
    });
    return () => {
      cancelled = true;
    };
  }, [period]);

  useEffect(() => {
    let cancelled = false;
    const hotelId = getReviewsExplorerHotelId();
    fetchRiskAlertsForPeriod(period, hotelId).then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setRiskAlertsApi({
          loading: false,
          data: result.data,
          errorMessage: null,
        });
      } else {
        setRiskAlertsApi({
          loading: false,
          data: null,
          errorMessage: result.error,
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [period]);

  useEffect(() => {
    let cancelled = false;
    const hotelId = getReviewsExplorerHotelId();
    fetchDataStrengthForPeriod(period, hotelId).then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setDataStrengthApi({
          loading: false,
          data: result.data,
          errorMessage: null,
        });
      } else {
        setDataStrengthApi({
          loading: false,
          data: null,
          errorMessage: result.error,
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [period]);

  useEffect(() => {
    let cancelled = false;
    const hotelId = getReviewsExplorerHotelId();
    fetchPainPointsIndexForPeriod(period, hotelId).then((result) => {
      if (cancelled) return;
      if (!result.ok) {
        setPainPointsIndexApi({
          loading: false,
          fromApi: false,
          items: [],
          errorMessage: result.error,
        });
        return;
      }
      setPainPointsIndexApi({
        loading: false,
        fromApi: true,
        items: result.data,
        errorMessage: null,
      });
    });
    return () => {
      cancelled = true;
    };
  }, [period]);

  useEffect(() => {
    let cancelled = false;
    const hotelId = getReviewsExplorerHotelId();
    fetchTrendSeriesForPeriod(period, hotelId).then((result) => {
      if (cancelled) return;
      if (result.status === "ok") {
        setTrendApi({
          loading: false,
          data: result.data,
          errorMessage: null,
          isEmpty: false,
        });
      } else if (result.status === "error") {
        setTrendApi({
          loading: false,
          data: null,
          errorMessage: result.message,
          isEmpty: false,
        });
      } else {
        setTrendApi({
          loading: false,
          data: null,
          errorMessage: null,
          isEmpty: true,
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [period]);

  const displayHero: HeroKpis | null =
    heroApi.status === "ok" ? heroApi.data : null;

  const displayExecutive: ExecutiveKpi[] =
    heroApi.status === "ok" ? heroApi.executiveKpis : [];

  const painPointsIndexEmptyFromApi =
    painPointsIndexApi.fromApi &&
    painPointsIndexApi.items.length === 0 &&
    !painPointsIndexApi.loading &&
    painPointsIndexApi.errorMessage === null;

  return (
    <div className="mx-auto max-w-[1400px] space-y-12 p-8 lg:p-12">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-label text-on-surface-variant/50 text-[10px] uppercase tracking-[0.2em]">
            Período de análisis
          </p>
        </div>
        <div
          className="bg-surface-container-low flex shrink-0 flex-wrap gap-1 rounded-lg p-1"
          role="tablist"
          aria-label="Rango temporal del dashboard"
        >
          {PERIOD_OPTIONS.map(({ id, label }) => {
            const active = period === id;
            return (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => {
                  setPeriod(id);
                  setHeroApi({ status: "loading" });
                  setTrendApi({
                    loading: true,
                    data: null,
                    errorMessage: null,
                    isEmpty: false,
                  });
                  setDataStrengthApi({
                    loading: true,
                    data: null,
                    errorMessage: null,
                  });
                  setRiskAlertsApi({
                    loading: true,
                    data: null,
                    errorMessage: null,
                  });
                  setCategoryScoresApi({
                    loading: true,
                    items: [],
                    errorMessage: null,
                  });
                  setTopInsightsApi({
                    loading: true,
                    strengths: [],
                    painPoints: [],
                    errorMessage: null,
                  });
                  setPainPointsIndexApi({
                    loading: true,
                    fromApi: false,
                    items: [],
                    errorMessage: null,
                  });
                }}
                className={`font-label rounded-md px-4 py-2 text-[11px] uppercase tracking-widest transition-all duration-300 ease-in-out ${
                  active
                    ? "bg-surface-container text-primary shadow-[0px_12px_32px_rgba(225,226,237,0.04)]"
                    : "text-on-surface/40 hover:bg-surface hover:text-on-surface"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </header>

      {heroApi.status === "error" && (
        <div
          className="bg-error/10 text-error border-error/20 rounded-card border px-4 py-3 text-sm"
          role="alert"
        >
          No se pudieron cargar los KPIs del servidor ({heroApi.message}). Los
          bloques de sentimiento y resumen ejecutivo no mostrarán datos hasta
          que la conexión se restablezca.
        </div>
      )}

      {trendApi.errorMessage !== null && (
        <div
          className="bg-error/10 text-error border-error/20 rounded-card border px-4 py-3 text-sm"
          role="alert"
        >
          No se pudo cargar la serie temporal ({trendApi.errorMessage}). No se
          muestra ninguna tendencia sustituta.
        </div>
      )}

      {trendApi.isEmpty && !trendApi.loading && (
        <div
          className="bg-on-surface-variant/10 text-on-surface-variant rounded-card border border-white/5 px-4 py-3 text-sm"
          role="status"
        >
          No hay puntos de sentimiento mensual en el período seleccionado.
        </div>
      )}

      {dataStrengthApi.errorMessage !== null && (
        <div
          className="bg-error/10 text-error border-error/20 rounded-card border px-4 py-3 text-sm"
          role="alert"
        >
          No se pudo cargar Data Strength ({dataStrengthApi.errorMessage}). Esta
          sección quedará vacía hasta que los datos estén disponibles.
        </div>
      )}

      {riskAlertsApi.errorMessage !== null && (
        <div
          className="bg-error/10 text-error border-error/20 rounded-card border px-4 py-3 text-sm"
          role="alert"
        >
          No se pudo cargar Riesgo Reputacional ({riskAlertsApi.errorMessage}).
          Esta sección quedará vacía hasta que los datos estén disponibles.
        </div>
      )}

      {categoryScoresApi.errorMessage !== null && (
        <div
          className="bg-error/10 text-error border-error/20 rounded-card border px-4 py-3 text-sm"
          role="alert"
        >
          No se pudieron cargar los tópicos por categoría (
          {categoryScoresApi.errorMessage}). No se muestran scores sustitutos.
        </div>
      )}

      {topInsightsApi.errorMessage !== null && (
        <div
          className="bg-error/10 text-error border-error/20 rounded-card border px-4 py-3 text-sm"
          role="alert"
        >
          No se pudieron cargar Top Insights ({topInsightsApi.errorMessage}). No
          se muestran rankings sustitutos.
        </div>
      )}

      {painPointsIndexApi.errorMessage !== null && (
        <div
          className="bg-error/10 text-error border-error/20 rounded-card border px-4 py-3 text-sm"
          role="alert"
        >
          No se pudo cargar Pain Points Index ({painPointsIndexApi.errorMessage}
          ). No se muestran tarjetas sustitutas.
        </div>
      )}

      <HeroKpisSection
        data={displayHero}
        loading={heroApi.status === "loading"}
      />
      <section>
        <SectionDivider label="📈 Tendencia del Sentimiento · Serie Temporal" />
        <TrendChart
          data={trendApi.data}
          loading={trendApi.loading}
          isEmpty={trendApi.isEmpty}
          fetchError={trendApi.errorMessage !== null}
        />
      </section>
      <DataStrengthSection
        data={dataStrengthApi.data}
        loading={dataStrengthApi.loading}
      />
      <RiskAlertsSection
        data={riskAlertsApi.data}
        loading={riskAlertsApi.loading}
      />
      <CategoryGrid
        items={categoryScoresApi.items}
        loading={categoryScoresApi.loading}
      />
      <TopInsightsSection
        strengths={topInsightsApi.strengths}
        painPoints={topInsightsApi.painPoints}
        loading={topInsightsApi.loading}
      />
      <PainPointsIndexSection
        items={painPointsIndexApi.items}
        loading={painPointsIndexApi.loading}
        emptyFromApi={painPointsIndexEmptyFromApi}
        loadError={painPointsIndexApi.errorMessage !== null}
      />
      <ExecutiveSummarySection
        items={displayExecutive}
        loading={heroApi.status === "loading"}
      />
      <AdvancedMetricsSection data={advancedMetrics} />
      <DashboardCanvasFooter note={dashboardFooterNote} />
    </div>
  );
}
