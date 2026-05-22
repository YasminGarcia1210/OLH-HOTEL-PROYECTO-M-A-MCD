"use client";

import { usePathname } from "next/navigation";

import { AuthProvider } from "@/components/auth/AuthProvider";
import { MobileBottomNav } from "@/components/layout/MobileBottomNav";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export function ConditionalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login";

  if (isAuthPage) return <>{children}</>;

  return (
    <AuthProvider>
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col md:ml-64">
        <TopBar />
        <div className="flex-1 pb-20 md:pb-0">{children}</div>
      </div>
      <MobileBottomNav />
    </AuthProvider>
  );
}
