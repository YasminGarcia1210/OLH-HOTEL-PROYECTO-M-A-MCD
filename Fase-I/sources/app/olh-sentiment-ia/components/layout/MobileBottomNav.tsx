"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/dashboard", label: "DASHBOARD", icon: "dashboard" },
  { href: "/dashboard/reviews", label: "REVIEWS", icon: "manage_search" },
  { href: "/upload", label: "UPLOAD", icon: "cloud_upload" },
  { href: "/admin", label: "SETTINGS", icon: "settings" },
] as const;

export function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="border-surface-variant/10 fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t bg-surface px-4 md:hidden">
      {items.map((item) => {
        const active =
          item.label === "DASHBOARD"
            ? pathname === "/dashboard" || pathname === "/"
            : item.label === "REVIEWS"
              ? pathname === "/dashboard/reviews"
              : pathname === item.href ||
                (item.href === "/admin" && pathname?.startsWith("/admin"));
        return (
          <Link
            key={`${item.href}-${item.label}`}
            href={item.href}
            className={`flex flex-col items-center gap-1 ${active ? "text-gold-bright" : "text-on-surface/60"}`}
          >
            <span
              className="material-symbols-outlined"
              style={
                active
                  ? {
                      fontVariationSettings:
                        "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24",
                    }
                  : undefined
              }
            >
              {item.icon}
            </span>
            <span className="font-label text-[10px] uppercase tracking-tighter">
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
