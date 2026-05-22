"use client";

import type { TrendSeries } from "@/lib/mock-data";
import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Props = {
  data: TrendSeries | null;
  loading?: boolean;
  /** Respuesta correcta pero sin filas en el período. */
  isEmpty?: boolean;
  /** Fallo de red o HTTP (además del banner superior, opcional). */
  fetchError?: boolean;
};

function yAxisFromValues(values: number[]): {
  domain: [number, number];
  ticks: number[];
} {
  const nums = values.filter(
    (v) => typeof v === "number" && !Number.isNaN(v),
  );
  if (nums.length === 0) {
    return { domain: [50, 100], ticks: [60, 70, 80, 90, 100] };
  }
  const minV = Math.min(...nums);
  const maxV = Math.max(...nums);
  if (minV >= 50 && maxV <= 100) {
    return { domain: [50, 100], ticks: [60, 70, 80, 90, 100] };
  }
  const pad = 10;
  let low = Math.max(0, Math.floor((minV - pad) / 5) * 5);
  let high = Math.min(100, Math.ceil((maxV + pad) / 5) * 5);
  if (high - low < 15) {
    const mid = (minV + maxV) / 2;
    low = Math.max(0, Math.floor((mid - 12) / 5) * 5);
    high = Math.min(100, Math.ceil((mid + 12) / 5) * 5);
  }
  const ticks: number[] = [];
  for (let t = low; t <= high; t += 5) {
    ticks.push(t);
  }
  if (ticks.length > 8) {
    const step = Math.max(10, Math.round((high - low) / 4 / 5) * 5);
    const sparse: number[] = [];
    for (let t = low; t <= high; t += step) {
      sparse.push(t);
    }
    if (sparse[sparse.length - 1] !== high) sparse.push(high);
    return { domain: [low, high], ticks: sparse };
  }
  return { domain: [low, high], ticks };
}

export function TrendChart({
  data,
  loading = false,
  isEmpty = false,
  fetchError = false,
}: Props) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.months.map((name, i) => ({
      name,
      score: data.values[i] ?? 0,
    }));
  }, [data]);

  const yAxis = useMemo(
    () => yAxisFromValues(data?.values ?? []),
    [data?.values],
  );

  const showSkeleton = !mounted || loading;
  const showPlaceholder =
    !loading && !data && (isEmpty || fetchError);

  return (
    <div className="border-surface-variant/10 bg-surface-container rounded-card border p-8">
      <div className="mb-8 flex items-center justify-between">
        <h3 className="font-headline text-lg italic">
          {data?.title ?? "Tendencia del sentimiento"}
        </h3>
        {data?.dateRangeLabel ? (
          <span className="text-on-surface-variant/40 text-xs">
            {data.dateRangeLabel}
          </span>
        ) : null}
      </div>
      <div className="relative h-[250px] w-full min-h-[250px] min-w-0">
        {showSkeleton ? (
          <div className="bg-surface-container-high/50 h-full w-full animate-pulse rounded" />
        ) : showPlaceholder ? (
          <div
            className="text-on-surface-variant/70 font-body flex h-full items-center justify-center rounded border border-white/5 bg-surface-container-low/50 px-4 text-center text-sm"
            role="status"
          >
            {fetchError
              ? "No se pudo cargar la serie temporal."
              : "No hay datos de sentimiento en el período seleccionado."}
          </div>
        ) : data ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#d4a847" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#d4a847" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                stroke="rgba(255,255,255,0.05)"
                vertical={false}
              />
              <XAxis
                dataKey="name"
                tick={{ fill: "#8b95a8", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={yAxis.domain}
                ticks={yAxis.ticks}
                tick={{ fill: "#8b95a8", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={36}
              />
              <Tooltip
                contentStyle={{
                  background: "#1d1f27",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "10px",
                  fontSize: 12,
                }}
                labelStyle={{ color: "#e1e2ed" }}
                formatter={(value) => [
                  `${value != null ? value : "—"}%`,
                  "Sentimiento",
                ]}
              />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#d4a847"
                strokeWidth={2}
                fill="url(#trendFill)"
                dot={{ r: 3, fill: "#d4a847", strokeWidth: 0 }}
                activeDot={{ r: 4 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : null}
      </div>
    </div>
  );
}
