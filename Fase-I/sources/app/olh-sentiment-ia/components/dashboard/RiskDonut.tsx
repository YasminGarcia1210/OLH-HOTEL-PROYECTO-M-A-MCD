"use client";

import { useEffect, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";

const OK = 60;
const RISK = 40;

const data = [
  { name: "ok", value: OK, fill: "#3ddc97" },
  { name: "risk", value: RISK, fill: "#ff6b6b" },
];

type Props = {
  centerPercent: number;
  centerSubtext: string;
  caption: string;
};

export function RiskDonut({ centerPercent, centerSubtext, caption }: Props) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <div className="border-surface-variant/10 bg-surface-container rounded-card flex h-full w-full flex-col items-center justify-center border p-8 text-center">
      <h3 className="mb-6 text-sm font-bold">Umbral de Riesgo</h3>
      <div className="relative mb-6 h-44 w-44 min-h-[176px] min-w-[176px]">
        {!mounted ? (
          <div className="bg-surface-container-high/50 h-full w-full animate-pulse rounded-full" />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius="78%"
                outerRadius="100%"
                startAngle={90}
                endAngle={-270}
                stroke="none"
                paddingAngle={0}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        )}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-headline text-warn-orange text-3xl font-bold">
            {centerPercent}%
          </span>
          <span className="text-on-surface-variant/40 mt-1 text-[10px] leading-tight">
            {centerSubtext.split("\n").map((line) => (
              <span key={line} className="block">
                {line}
              </span>
            ))}
          </span>
        </div>
      </div>
      <p className="text-on-surface-variant/40 text-xs">{caption}</p>
    </div>
  );
}
