"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <span
        className="material-symbols-outlined text-on-surface/35 inline-flex size-9 shrink-0 items-center justify-center"
        aria-hidden
      >
        dark_mode
      </span>
    );
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="material-symbols-outlined text-on-surface/60 hover:text-primary active:scale-95 inline-flex size-9 shrink-0 items-center justify-center rounded-lg transition-all"
      aria-label={isDark ? "Activar modo claro" : "Activar modo oscuro"}
      aria-pressed={isDark}
    >
      {isDark ? "light_mode" : "dark_mode"}
    </button>
  );
}
