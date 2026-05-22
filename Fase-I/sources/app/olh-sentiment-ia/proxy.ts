import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login"];

function getJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get("access_token")?.value;
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // If the token itself has expired, redirect immediately on every navigation
  // instead of letting the user browse until an API call triggers the 401 flow.
  const payload = getJwtPayload(token);
  if (!payload || (typeof payload.exp === "number" && Date.now() / 1000 > payload.exp)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Rutas de administración: solo accesibles para rol 'admin'
  if (pathname.startsWith("/admin")) {
    if (payload?.rol !== "admin") {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.svg|.*\\.ico).*)"],
};
