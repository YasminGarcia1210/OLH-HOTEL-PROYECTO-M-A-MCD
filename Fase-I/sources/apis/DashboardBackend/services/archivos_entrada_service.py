"""
Cruce entre blobs bajo AZURE_BLOB_PREFIX_UPLOAD y la tabla log_archivos.
"""

from __future__ import annotations

import math
import os

import db
from config import Config
from repositories.log_archivos_repository import LogArchivosRepository
from services.azure_blob_upload_service import listar_blobs_por_prefijo, prefijo_blob_normalizado
_repo = LogArchivosRepository()

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


def _paginacion(page: int, page_size: int, total: int) -> dict:
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def _serializar_valor(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _serializar_fila_log(row: dict) -> dict:
    return {k: _serializar_valor(v) for k, v in row.items()}


def obtener_estado_archivos_entrada(
    limite: int | None = None,
    *,
    pipeline_page: int = 1,
    pipeline_page_size: int = _DEFAULT_PAGE_SIZE,
    pendientes_page: int = 1,
    pendientes_page_size: int = _DEFAULT_PAGE_SIZE,
) -> dict:
    """
    Lista blobs bajo el prefijo de subida (o todo el contenedor si el prefijo es vacío / raíz),
    filas paginadas de log_archivos (sin filtrar por origen), y blobs pendientes de lectura.
    """
    raw = (Config.AZURE_BLOB_PREFIX_UPLOAD or "").strip()
    # Vacío o solo barras → prefijo virtual "raíz": se listan todos los blobs del contenedor
    # (archivos sin carpeta, p. ej. `informe.csv`).

    ps = min(max(1, pipeline_page_size), _MAX_PAGE_SIZE)
    pp = min(max(1, pendientes_page_size), _MAX_PAGE_SIZE)
    p_page = max(1, pipeline_page)
    q_page = max(1, pendientes_page)

    prefijo_display = prefijo_blob_normalizado(raw).rstrip("/")
    blobs, truncado = listar_blobs_por_prefijo(raw, limite=limite)

    with db.get_connection() as conn:
        drive_set = _repo.listar_drive_id_origen(conn)
        total_pipeline = _repo.contar_log_archivos(conn)
        offset_pipeline = (p_page - 1) * ps
        en_pipeline_raw = _repo.listar_log_archivos_paginado(
            conn, offset_pipeline, ps
        )
        basenames = list({os.path.basename(b["blob_path"]) for b in blobs})
        nombres_en_log = _repo.nombres_origen_presentes(conn, basenames)

    pendientes_full: list[dict] = []
    for b in blobs:
        path = b["blob_path"]
        base = os.path.basename(path)
        if path in drive_set:
            continue
        if base in nombres_en_log:
            continue
        pendientes_full.append(b)

    total_pendientes = len(pendientes_full)
    off_q = (q_page - 1) * pp
    pendientes_slice = pendientes_full[off_q : off_q + pp]

    en_pipeline = [_serializar_fila_log(r) for r in en_pipeline_raw]

    out: dict = {
        "prefijo": prefijo_display,
        "pendientes": pendientes_slice,
        "en_pipeline": en_pipeline,
        "paginacion_pendientes": _paginacion(q_page, pp, total_pendientes),
        "paginacion_pipeline": _paginacion(p_page, ps, total_pipeline),
    }
    if limite is not None:
        out["truncado"] = truncado
    return out
