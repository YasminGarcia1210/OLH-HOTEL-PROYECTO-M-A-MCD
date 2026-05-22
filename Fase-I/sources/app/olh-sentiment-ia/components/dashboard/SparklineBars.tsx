"use client";

import { useEffect, useState } from "react";

type Props = {
  values: number[];
};

export function SparklineBars({ values }: Props) {
  const maxVal = Math.max(...values);
  const [heights, setHeights] = useState<number[]>(() =>
    values.map(() => 0),
  );

  useEffect(() => {
    const t = requestAnimationFrame(() => {
      setHeights(values.map((v) => (maxVal > 0 ? (v / maxVal) * 100 : 0)));
    });
    return () => cancelAnimationFrame(t);
  }, [values, maxVal]);

  return (
    <div className="mt-4 flex h-8 items-end justify-center gap-1">
      {values.map((v, i) => (
        <div
          key={`${v}-${i}`}
          className="spark-bar"
          style={{
            width: 6,
            height: `${heights[i] ?? 0}%`,
            backgroundColor: v === maxVal ? "#d4a847" : "#5ba4f5",
          }}
        />
      ))}
    </div>
  );
}
