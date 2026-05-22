import { fetchWithAuth } from "@/lib/fetch-with-auth";
import { getDashboardApiBaseUrl } from "@/lib/reviews-api";
import type { DashboardEnvelope } from "@/lib/reviews-api";

export type Rol = "admin" | "viewer";

export type Usuario = {
  id: number;
  nombre: string;
  username: string;
  hotel_id: number | null;
  hotel_nombre: string | null;
  rol: Rol;
  activo: boolean;
  creado_en: string;
};

export type UsuariosListResponse = {
  items: Usuario[];
  total: number;
  page: number;
  page_size: number;
};

export type CreateUsuarioPayload = {
  nombre: string;
  username: string;
  password: string;
  hotel_id?: number | null;
  rol?: Rol;
};

export type UpdateUsuarioPayload = {
  nombre?: string;
  username?: string;
  password?: string;
  hotel_id?: number | null;
  rol?: Rol;
  activo?: boolean;
};

function base() {
  return getDashboardApiBaseUrl();
}

async function safeJson<T>(res: Response): Promise<DashboardEnvelope<T>> {
  try {
    const body = (await res.json()) as DashboardEnvelope<T>;
    if (!res.ok) {
      return {
        ok: false,
        data: null,
        error: body.error ?? { codigo: "HTTP_ERROR", mensaje: `HTTP ${res.status}` },
      };
    }
    return body;
  } catch {
    return {
      ok: false,
      data: null,
      error: { codigo: "RESPUESTA_INVALIDA", mensaje: `Respuesta no es JSON (HTTP ${res.status})` },
    };
  }
}

function netError<T>(e: unknown): DashboardEnvelope<T> {
  return {
    ok: false,
    data: null,
    error: { codigo: "RED", mensaje: e instanceof Error ? e.message : "Error de red" },
  };
}

export async function fetchUsuarios(
  page = 1,
  pageSize = 20,
): Promise<DashboardEnvelope<UsuariosListResponse>> {
  try {
    const res = await fetchWithAuth(
      `${base()}/api/v1/usuarios?page=${page}&page_size=${pageSize}`,
    );
    return safeJson<UsuariosListResponse>(res);
  } catch (e) {
    return netError(e);
  }
}

export async function createUsuario(
  payload: CreateUsuarioPayload,
): Promise<DashboardEnvelope<Usuario>> {
  try {
    const res = await fetchWithAuth(`${base()}/api/v1/usuarios`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return safeJson<Usuario>(res);
  } catch (e) {
    return netError(e);
  }
}

export async function updateUsuario(
  id: number,
  payload: UpdateUsuarioPayload,
): Promise<DashboardEnvelope<Usuario>> {
  try {
    const res = await fetchWithAuth(`${base()}/api/v1/usuarios/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return safeJson<Usuario>(res);
  } catch (e) {
    return netError(e);
  }
}

export async function deleteUsuario(
  id: number,
): Promise<DashboardEnvelope<{ id: number; eliminado: boolean }>> {
  try {
    const res = await fetchWithAuth(`${base()}/api/v1/usuarios/${id}`, {
      method: "DELETE",
    });
    return safeJson<{ id: number; eliminado: boolean }>(res);
  } catch (e) {
    return netError(e);
  }
}
