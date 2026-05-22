"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useAuth } from "@/components/auth/AuthProvider";
import { TopicosSection } from "@/components/admin/TopicosSection";
import { fetchHoteles, type Hotel } from "@/lib/hoteles-api";
import { getReviewsExplorerHotelId } from "@/lib/reviews-api";
import {
  createUsuario,
  deleteUsuario,
  fetchUsuarios,
  updateUsuario,
  type CreateUsuarioPayload,
  type UpdateUsuarioPayload,
  type Usuario,
} from "@/lib/usuarios-api";

// ── Types ─────────────────────────────────────────────────────────────────────

type ToastType = "success" | "error";
type ToastItem = { id: number; type: ToastType; message: string };

type ModalMode = "create" | "edit";

type FormState = {
  nombre: string;
  username: string;
  password: string;
  hotel_id: string;
  rol: "admin" | "viewer";
  activo: boolean;
};

const EMPTY_FORM: FormState = {
  nombre: "",
  username: "",
  password: "",
  hotel_id: "",
  rol: "viewer",
  activo: true,
};

const PAGE_SIZE = 15;

// ── Portal helper ─────────────────────────────────────────────────────────────
// Renders children directly on document.body so that fixed + inset-0 is always
// relative to the viewport, unaffected by any parent stacking context or transform.

function Portal({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;
  return createPortal(children, document.body);
}

// ── Small primitives ──────────────────────────────────────────────────────────

function Chip({ activo }: { activo: boolean }) {
  return (
    <span className={`tag ${activo ? "tag-ok" : "tag-crit"}`}>
      {activo ? "Activo" : "Inactivo"}
    </span>
  );
}

function IconBtn({
  icon,
  title,
  danger,
  disabled,
  loading,
  onClick,
}: {
  icon: string;
  title: string;
  danger?: boolean;
  disabled?: boolean;
  loading?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled || loading}
      className={`flex h-8 w-8 items-center justify-center rounded transition-colors ${
        disabled || loading
          ? "cursor-not-allowed opacity-20"
          : danger
            ? "text-on-surface/40 hover:bg-error/10 hover:text-error"
            : "text-on-surface/40 hover:bg-surface-container-high hover:text-gold-bright"
      }`}
    >
      <span
        className={`material-symbols-outlined ${loading ? "animate-spin" : ""}`}
        style={{ fontSize: 18 }}
      >
        {loading ? "progress_activity" : icon}
      </span>
    </button>
  );
}

function ToastList({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: number) => void;
}) {
  return (
    <div
      className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2"
      style={{ pointerEvents: "none" }}
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          style={{ pointerEvents: "auto" }}
          className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-sm shadow-xl ${
            t.type === "success"
              ? "border-tertiary/30 bg-surface-container-high"
              : "border-error/30 bg-surface-container-high"
          }`}
        >
          <span
            className={`material-symbols-outlined shrink-0 ${t.type === "success" ? "text-tertiary" : "text-error"}`}
            style={{ fontSize: 18 }}
          >
            {t.type === "success" ? "check_circle" : "error"}
          </span>
          <span className="flex-1 text-on-surface">{t.message}</span>
          <button
            type="button"
            onClick={() => onDismiss(t.id)}
            className="shrink-0 text-on-surface/40 transition-colors hover:text-on-surface"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
              close
            </span>
          </button>
        </div>
      ))}
    </div>
  );
}

function ErrorBanner({ msg, onClose }: { msg: string; onClose: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-error/20 bg-error/10 px-4 py-3 text-sm text-error">
      <span className="material-symbols-outlined mt-0.5 shrink-0" style={{ fontSize: 16 }}>
        error
      </span>
      <span className="flex-1">{msg}</span>
      <button type="button" onClick={onClose} className="shrink-0 opacity-60 hover:opacity-100">
        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
          close
        </span>
      </button>
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function UsuarioModal({
  mode,
  initial,
  isSelf,
  currentUserHotelId,
  hoteles,
  onClose,
  onSaved,
}: {
  mode: ModalMode;
  initial: Usuario | null;
  isSelf: boolean;
  currentUserHotelId: number | null;
  hoteles: Hotel[];
  onClose: () => void;
  onSaved: (u: Usuario) => void;
}) {
  const [form, setForm] = useState<FormState>(() => {
    if (initial) {
      return {
        nombre: initial.nombre,
        username: initial.username,
        password: "",
        hotel_id: initial.hotel_id != null ? String(initial.hotel_id) : "",
        rol: initial.rol,
        activo: initial.activo,
      };
    }
    return {
      ...EMPTY_FORM,
      // Pre-fill hotel_id for scoped admins so it's always sent in create
      hotel_id: currentUserHotelId != null ? String(currentUserHotelId) : "",
    };
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstRef.current?.focus();
  }, []);

  function set(key: keyof FormState, value: string | boolean) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);

    const hotelId = form.hotel_id.trim()
      ? parseInt(form.hotel_id.trim(), 10)
      : null;

    let result;
    if (mode === "create") {
      const payload: CreateUsuarioPayload = {
        nombre: form.nombre.trim(),
        username: form.username.trim(),
        password: form.password,
        hotel_id: hotelId,
        rol: form.rol,
      };
      result = await createUsuario(payload);
    } else {
      const payload: UpdateUsuarioPayload = {
        nombre: form.nombre.trim(),
        username: form.username.trim(),
        hotel_id: hotelId,
        rol: isSelf ? undefined : form.rol,
        activo: form.activo,
      };
      if (form.password) payload.password = form.password;
      result = await updateUsuario(initial!.id, payload);
    }

    setSaving(false);

    if (!result.ok || !result.data) {
      setError(result.error?.mensaje ?? "Error inesperado");
      return;
    }
    onSaved(result.data);
  }

  return (
    <Portal>
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-md rounded-[14px] bg-surface-container-high p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="font-headline text-lg font-bold text-on-background">
            {mode === "create" ? "Nuevo usuario" : "Editar usuario"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-on-surface/40 hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {error && (
          <div className="mb-4">
            <ErrorBanner msg={error} onClose={() => setError(null)} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Nombre completo" required>
            <input
              ref={firstRef}
              type="text"
              value={form.nombre}
              onChange={(e) => set("nombre", e.target.value)}
              placeholder="Ana García"
              required
              maxLength={120}
              className={inputCls}
            />
          </Field>

          <Field label="Username" required>
            <input
              type="text"
              value={form.username}
              onChange={(e) => set("username", e.target.value)}
              placeholder="ana.garcia"
              required
              maxLength={100}
              className={inputCls}
            />
          </Field>

          <Field
            label={mode === "edit" ? "Nueva contraseña (opcional)" : "Contraseña"}
            required={mode === "create"}
          >
            <input
              type="password"
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              placeholder={mode === "edit" ? "Dejar en blanco para no cambiar" : "Mínimo 8 caracteres"}
              required={mode === "create"}
              minLength={mode === "create" ? 8 : undefined}
              className={inputCls}
            />
          </Field>

          {currentUserHotelId != null ? (
            <div className="flex items-center gap-2 rounded border border-surface-variant/20 bg-surface-container px-3 py-2">
              <span className="material-symbols-outlined text-on-surface/30" style={{ fontSize: 16 }}>
                hotel
              </span>
              <span className="font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
                Hotel asignado:
              </span>
              <span className="text-sm text-on-surface/70">
                {hoteles.find((h) => h.id === currentUserHotelId)?.nombre ?? `ID ${currentUserHotelId}`}
              </span>
            </div>
          ) : (
            <Field label="Hotel (opcional)">
              <select
                value={form.hotel_id}
                onChange={(e) => set("hotel_id", e.target.value)}
                className={inputCls}
              >
                <option value="">Sin hotel — acceso global</option>
                {hoteles.map((h) => (
                  <option key={h.id} value={String(h.id)}>
                    {h.nombre}{h.ciudad ? ` — ${h.ciudad}` : ""}
                  </option>
                ))}
              </select>
            </Field>
          )}

          <Field label="Rol" required>
            <select
              value={form.rol}
              onChange={(e) => set("rol", e.target.value as "admin" | "viewer")}
              disabled={isSelf}
              title={isSelf ? "No puedes cambiar tu propio rol" : undefined}
              className={`${inputCls} ${isSelf ? "cursor-not-allowed opacity-40" : ""}`}
            >
              <option value="viewer">Viewer — solo lectura del dashboard</option>
              <option value="admin">Admin — acceso total incluyendo configuración</option>
            </select>
          </Field>

          {mode === "edit" && (
            <div className="flex items-center gap-3">
              <button
                type="button"
                role="switch"
                aria-checked={form.activo}
                disabled={isSelf}
                onClick={() => set("activo", !form.activo)}
                title={isSelf ? "No puedes desactivar tu propia cuenta" : undefined}
                className={`relative h-6 w-11 shrink-0 overflow-hidden rounded-full transition-colors ${
                  isSelf
                    ? "cursor-not-allowed opacity-30 bg-tertiary"
                    : form.activo
                      ? "bg-tertiary"
                      : "bg-surface-container-highest"
                }`}
              >
                <span
                  className={`absolute left-0 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                    form.activo ? "translate-x-5" : "translate-x-0.5"
                  }`}
                />
              </button>
              <span className={`font-label text-xs uppercase tracking-widest ${isSelf ? "text-on-surface/30" : "text-on-surface/60"}`}>
                {form.activo ? "Activo" : "Inactivo"}
                {isSelf && (
                  <span className="ml-2 normal-case tracking-normal">(no modificable)</span>
                )}
              </span>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="font-label rounded px-4 py-2 text-xs uppercase tracking-widest text-on-surface/60 transition-colors hover:text-on-surface"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="gradient-gold font-label text-on-primary rounded px-5 py-2 text-xs font-bold uppercase tracking-widest transition-opacity disabled:opacity-50"
            >
              {saving ? "Guardando…" : mode === "create" ? "Crear" : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </Portal>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/60">
        {label}
        {required && <span className="ml-0.5 text-error">*</span>}
      </span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded border border-surface-variant/40 bg-surface-container px-3 py-2 text-sm text-on-surface placeholder-on-surface/30 outline-none transition focus:border-gold-bright/60 focus:ring-1 focus:ring-gold-bright/30";

// ── Delete confirm ────────────────────────────────────────────────────────────

function DeleteConfirmDialog({
  usuario,
  deleting,
  onConfirm,
  onCancel,
}: {
  usuario: Usuario;
  deleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Portal>
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-[14px] bg-surface-container-high p-6 shadow-2xl">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-error/10">
          <span className="material-symbols-outlined text-error">delete</span>
        </div>
        <h3 className="font-headline mb-2 text-lg font-bold text-on-background">
          Eliminar usuario
        </h3>
        <p className="mb-6 text-sm text-on-surface/60">
          ¿Eliminar a{" "}
          <span className="font-semibold text-on-surface">{usuario.nombre}</span>{" "}
          ({usuario.username})? Esta acción no se puede deshacer.
        </p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={deleting}
            className="font-label rounded px-4 py-2 text-xs uppercase tracking-widest text-on-surface/60 transition-colors hover:text-on-surface disabled:opacity-40"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={deleting}
            className="font-label flex items-center gap-2 rounded bg-error px-5 py-2 text-xs font-bold uppercase tracking-widest text-on-error transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {deleting && (
              <span className="material-symbols-outlined animate-spin" style={{ fontSize: 14 }}>
                progress_activity
              </span>
            )}
            {deleting ? "Eliminando…" : "Eliminar"}
          </button>
        </div>
      </div>
    </div>
    </Portal>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function AdminPageContent() {
  const { username: currentUsername, hotelId: currentUserHotelId } = useAuth();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [hoteles, setHoteles] = useState<Hotel[]>([]);
  const [modalMode, setModalMode] = useState<ModalMode | null>(null);
  const [editTarget, setEditTarget] = useState<Usuario | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Usuario | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [togglingIds, setTogglingIds] = useState<Set<number>>(new Set());
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastId = useRef(0);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function showToast(type: ToastType, message: string) {
    const id = ++toastId.current;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }

  function dismissToast(id: number) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  const loadPage = useCallback(async (p: number) => {
    setLoading(true);
    setFetchError(null);
    const result = await fetchUsuarios(p, PAGE_SIZE);
    setLoading(false);
    if (!result.ok || !result.data) {
      setFetchError(result.error?.mensaje ?? "Error al cargar usuarios");
      return;
    }
    setUsuarios(result.data.items);
    setTotal(result.data.total);
  }, []);

  useEffect(() => {
    loadPage(page);
  }, [page, loadPage]);

  // Fetch hotels once for the global-access admin's hotel selector
  useEffect(() => {
    if (currentUserHotelId === null) {
      fetchHoteles().then((res) => {
        if (res.ok && res.data) setHoteles(res.data);
      });
    }
  }, [currentUserHotelId]);

  function openCreate() {
    setEditTarget(null);
    setModalMode("create");
  }

  function openEdit(u: Usuario) {
    setEditTarget(u);
    setModalMode("edit");
  }

  function handleSaved(u: Usuario) {
    const wasCreate = modalMode === "create";
    setModalMode(null);
    if (wasCreate) {
      loadPage(page);
      showToast("success", "Usuario creado correctamente");
    } else {
      setUsuarios((prev) => prev.map((x) => (x.id === u.id ? u : x)));
      showToast("success", "Usuario actualizado correctamente");
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    const result = await deleteUsuario(deleteTarget.id);
    setDeleting(false);
    if (!result.ok) {
      setDeleteTarget(null);
      showToast("error", result.error?.mensaje ?? "Error al eliminar usuario");
      return;
    }
    setUsuarios((prev) => prev.filter((u) => u.id !== deleteTarget.id));
    setTotal((t) => t - 1);
    setDeleteTarget(null);
    showToast("success", "Usuario eliminado correctamente");
  }

  async function toggleActivo(u: Usuario) {
    setTogglingIds((prev) => new Set(prev).add(u.id));
    const result = await updateUsuario(u.id, { activo: !u.activo });
    setTogglingIds((prev) => {
      const s = new Set(prev);
      s.delete(u.id);
      return s;
    });
    if (!result.ok || !result.data) {
      showToast("error", result.error?.mensaje ?? "Error al actualizar estado");
      return;
    }
    setUsuarios((prev) => prev.map((x) => (x.id === u.id ? result.data! : x)));
    showToast(
      "success",
      result.data.activo ? "Usuario activado correctamente" : "Usuario desactivado correctamente",
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-8 lg:p-12">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-headline text-2xl font-bold text-on-background">
            Gestión de usuarios
          </h1>
          <p className="mt-1 text-sm text-on-surface/50">
            {total} usuario{total !== 1 ? "s" : ""} registrado{total !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="gradient-gold font-label text-on-primary flex shrink-0 items-center gap-2 rounded-md px-5 py-2.5 text-[0.6875rem] font-bold uppercase tracking-widest transition-transform active:scale-95"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
            person_add
          </span>
          Nuevo usuario
        </button>
      </div>

      {/* Table card */}
      <div className="rounded-[14px] bg-surface-container overflow-hidden">
        {/* Table header */}
        <div className="border-b border-surface-variant/20 px-6 py-4">
          <span className="font-label text-[0.6875rem] uppercase tracking-widest text-on-surface/40">
            Usuarios del sistema
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-3 py-20 text-on-surface/40">
            <span className="material-symbols-outlined animate-spin" style={{ fontSize: 20 }}>
              progress_activity
            </span>
            <span className="text-sm">Cargando…</span>
          </div>
        ) : fetchError ? (
          <div className="flex flex-col items-center gap-3 py-20 text-center">
            <span className="material-symbols-outlined text-error" style={{ fontSize: 32 }}>
              error_outline
            </span>
            <p className="text-sm text-on-surface/60">{fetchError}</p>
            <button
              type="button"
              onClick={() => loadPage(page)}
              className="font-label mt-1 text-[0.6875rem] uppercase tracking-widest text-gold-bright hover:underline"
            >
              Reintentar
            </button>
          </div>
        ) : usuarios.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-20 text-center">
            <span className="material-symbols-outlined text-on-surface/20" style={{ fontSize: 40 }}>
              group
            </span>
            <p className="text-sm text-on-surface/40">No hay usuarios registrados.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-variant/20">
                  {["ID", "Nombre", "Username", "Hotel", "Rol", "Estado", "Creado", ""].map(
                    (h) => (
                      <th
                        key={h}
                        className="font-label px-6 py-3 text-left text-[0.625rem] uppercase tracking-widest text-on-surface/40"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u, i) => {
                  const isSelf = u.username === currentUsername;
                  return (
                    <tr
                      key={u.id}
                      className={`border-b border-surface-variant/10 transition-colors hover:bg-surface-container-high ${
                        i % 2 === 0 ? "" : "bg-surface-container-low/30"
                      }`}
                    >
                      <td className="px-6 py-4 text-on-surface/40">{u.id}</td>
                      <td className="px-6 py-4 font-medium text-on-surface">{u.nombre}</td>
                      <td className="px-6 py-4 font-mono text-on-surface/70">
                        <span className="flex items-center gap-2">
                          {u.username}
                          {isSelf && (
                            <span
                              className="tag"
                              style={{ background: "rgba(242,195,95,0.1)", color: "#f2c35f" }}
                              title="Tu cuenta"
                            >
                              Tú
                            </span>
                          )}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-on-surface/50">
                        {u.hotel_id != null ? (
                          <span className="tag" style={{ background: "rgba(212,168,71,0.08)", color: "#d4a847" }}>
                            {u.hotel_nombre ?? `Hotel ${u.hotel_id}`}
                          </span>
                        ) : (
                          <span className="text-xs text-on-surface/30">Global</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {u.rol === "admin" ? (
                          <span className="tag" style={{ background: "rgba(242,195,95,0.1)", color: "#f2c35f" }}>Admin</span>
                        ) : (
                          <span className="tag" style={{ background: "rgba(188,199,222,0.1)", color: "#bcc7de" }}>Viewer</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <Chip activo={u.activo} />
                      </td>
                      <td className="px-6 py-4 text-xs text-on-surface/40">
                        {new Date(u.creado_en).toLocaleDateString("es-CO", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1">
                          <IconBtn
                            icon="edit"
                            title="Editar"
                            onClick={() => openEdit(u)}
                          />
                          <IconBtn
                            icon={u.activo ? "toggle_on" : "toggle_off"}
                            title={isSelf ? "No puedes desactivar tu propia cuenta" : u.activo ? "Desactivar" : "Activar"}
                            disabled={isSelf}
                            loading={togglingIds.has(u.id)}
                            onClick={() => toggleActivo(u)}
                          />
                          <IconBtn
                            icon="delete"
                            title={isSelf ? "No puedes eliminar tu propia cuenta" : "Eliminar"}
                            danger
                            disabled={isSelf}
                            onClick={() => setDeleteTarget(u)}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && !fetchError && totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-surface-variant/20 px-6 py-3">
            <span className="font-label text-[0.6875rem] text-on-surface/40">
              Página {page} de {totalPages}
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="flex h-8 w-8 items-center justify-center rounded text-on-surface/40 transition-colors hover:bg-surface-container-high hover:text-on-surface disabled:opacity-20"
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                  chevron_left
                </span>
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="flex h-8 w-8 items-center justify-center rounded text-on-surface/40 transition-colors hover:bg-surface-container-high hover:text-on-surface disabled:opacity-20"
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                  chevron_right
                </span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {modalMode && (
        <UsuarioModal
          mode={modalMode}
          initial={editTarget}
          isSelf={editTarget?.username === currentUsername}
          currentUserHotelId={currentUserHotelId ?? null}
          hoteles={hoteles}
          onClose={() => setModalMode(null)}
          onSaved={handleSaved}
        />
      )}

      {deleteTarget && (
        <DeleteConfirmDialog
          usuario={deleteTarget}
          deleting={deleting}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      {/* ── Tópicos ── */}
      <div className="border-t border-surface-variant/20 pt-8">
        <TopicosSection
          hotelId={currentUserHotelId ?? getReviewsExplorerHotelId()}
          onToast={showToast}
        />
      </div>

      <ToastList toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
