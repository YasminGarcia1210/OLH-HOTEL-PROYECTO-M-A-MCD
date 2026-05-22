"""
Subida de bytes a Azure Blob Storage (un contenedor, prefijo virtual configurable).
"""

from __future__ import annotations

import logging

from azure.core.exceptions import HttpResponseError
from azure.storage.blob import BlobServiceClient

from config import Config
from services.exceptions import CredencialesAzureError, ListadoAzureError, SubidaAzureError

logger = logging.getLogger(__name__)


def _normalize_blob_name(name: str) -> str:
    return name.strip().lstrip("/")


def _ensure_trailing_slash_prefix(prefix: str) -> str:
    p = prefix.strip().strip("/")
    if not p:
        return ""
    return f"{p}/"


def _get_service() -> BlobServiceClient:
    conn = (Config.AZURE_STORAGE_CONNECTION_STRING or "").strip()
    if not conn:
        raise CredencialesAzureError(
            "AZURE_STORAGE_CONNECTION_STRING no está definida o está vacía."
        )
    try:
        return BlobServiceClient.from_connection_string(conn)
    except Exception as e:
        raise CredencialesAzureError(
            f"Error de autenticación con Azure Blob Storage: {e}"
        ) from e


def _container_name() -> str:
    name = (Config.AZURE_STORAGE_CONTAINER or "").strip()
    if not name:
        raise CredencialesAzureError("AZURE_STORAGE_CONTAINER no está definido o está vacío.")
    return name


def subir_bytes(nombre_blob: str, contenido: bytes, folder_prefix: str) -> str:
    """
    Sube bytes al contenedor configurado bajo folder_prefix + nombre_blob.

    Returns:
        Ruta del blob dentro del contenedor (p. ej. entrada/mi_archivo.csv).
    """
    prefix = _ensure_trailing_slash_prefix(folder_prefix)
    dest_name = _normalize_blob_name(prefix + nombre_blob)

    service = _get_service()
    container = service.get_container_client(_container_name())
    blob_client = container.get_blob_client(dest_name)

    if blob_client.exists():
        raise SubidaAzureError(
            f"Ya existe un blob en destino; no se sobrescribe: '{dest_name}'."
        )

    try:
        blob_client.upload_blob(contenido, overwrite=False)
        logger.info("Blob '%s' subido correctamente (%d bytes).", dest_name, len(contenido))
        return dest_name
    except CredencialesAzureError:
        raise
    except HttpResponseError as e:
        raise SubidaAzureError(
            f"Error HTTP {e.status_code} al subir '{dest_name}': {e}"
        ) from e
    except Exception as e:
        raise SubidaAzureError(f"Error inesperado al subir '{dest_name}': {e}") from e


def prefijo_blob_normalizado(folder_prefix: str) -> str:
    """Prefijo virtual con barra final, coherente con subir_bytes (p. ej. `entrada/`)."""
    return _ensure_trailing_slash_prefix(folder_prefix)


def _prefijos_excluidos_desde_config() -> list[str]:
    """
    Normaliza entradas tipo `limpios, backup` → `limpios/`, `backup/` para filtrar listados.
    """
    raw = (Config.AZURE_BLOB_LIST_EXCLUDE_PREFIXES or "").strip()
    if not raw:
        return []
    out: list[str] = []
    for part in raw.split(","):
        p = _ensure_trailing_slash_prefix(part)
        if p:
            out.append(p)
    return out


def _blob_bajo_prefijo_excluido(blob_name: str, exclude_prefixes: list[str]) -> bool:
    if not exclude_prefixes:
        return False
    for pref in exclude_prefixes:
        if blob_name.startswith(pref):
            return True
    return False


def _blob_es_nivel_directo(blob_name: str, prefix_with_slash: str) -> bool:
    """
    True si el blob está en el nivel del prefijo, sin segmentos extra (no subcarpetas).

    - Raíz (prefijo vacío): nombre sin `/` (p. ej. `informe.csv`).
    - Con prefijo `entrada/`: solo `entrada/archivo.csv`, no `entrada/sub/archivo.csv`.
    """
    if not prefix_with_slash:
        return "/" not in blob_name and bool(blob_name.strip())
    if not blob_name.startswith(prefix_with_slash):
        return False
    rest = blob_name[len(prefix_with_slash) :]
    return bool(rest) and "/" not in rest


def listar_blobs_por_prefijo(
    folder_prefix: str,
    *,
    limite: int | None = None,
) -> tuple[list[dict], bool]:
    """
    Lista blobs en el prefijo normalizado **solo un nivel**: no incluye blobs dentro de subcarpetas
    (p. ej. con prefijo `entrada/` se omite `entrada/sub/c.csv`; en raíz solo nombres sin `/`).

    Además omite rutas bajo los prefijos configurados en `AZURE_BLOB_LIST_EXCLUDE_PREFIXES`
    (p. ej. `limpios` para no listar CSV limpios del pipeline).

    Si el prefijo queda vacío, solo archivos en la raíz del contenedor (nombre sin `/`).

    Returns:
        (lista de { blob_path, tamano_bytes, ultima_modificacion }, truncado)
        truncado es True si se alcanzó `limite` y pudo haber más resultados.
    """
    prefix = prefijo_blob_normalizado(folder_prefix)
    exclude_prefixes = _prefijos_excluidos_desde_config()

    service = _get_service()
    container = service.get_container_client(_container_name())

    out: list[dict] = []
    truncado = False
    try:
        # Sin prefijo: raíz / todo el contenedor (name_starts_with vacío no filtra en la API de Azure)
        it = iter(
            container.list_blobs(name_starts_with=prefix) if prefix else container.list_blobs()
        )
        while True:
            try:
                blob = next(it)
            except StopIteration:
                break
            if _blob_bajo_prefijo_excluido(blob.name, exclude_prefixes):
                continue
            if not _blob_es_nivel_directo(blob.name, prefix):
                continue
            lm = getattr(blob, "last_modified", None)
            out.append(
                {
                    "blob_path": blob.name,
                    "tamano_bytes": getattr(blob, "size", None),
                    "ultima_modificacion": lm.isoformat() if lm is not None else None,
                }
            )
            if limite is not None and len(out) >= limite:
                try:
                    next(it)
                    truncado = True
                except StopIteration:
                    pass
                break
    except CredencialesAzureError:
        raise
    except HttpResponseError as e:
        ctx = f"prefijo '{prefix}'" if prefix else "raíz del contenedor (sin prefijo)"
        raise ListadoAzureError(
            f"Error HTTP {e.status_code} al listar blobs ({ctx}): {e}"
        ) from e
    except Exception as e:
        ctx = f"prefijo '{prefix}'" if prefix else "raíz del contenedor (sin prefijo)"
        raise ListadoAzureError(
            f"Error inesperado al listar blobs ({ctx}): {e}"
        ) from e

    return out, truncado
