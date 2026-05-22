"""
Orquestación: hash SHA-256, comprobación en log_archivos, subida a Azure Blob.
No inserta filas en log_archivos.
"""

from __future__ import annotations

import hashlib
import logging

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

import db
from config import Config
from repositories.log_archivos_repository import LogArchivosRepository
from services.azure_blob_upload_service import subir_bytes
from services.exceptions import ArchivoDuplicadoError

logger = logging.getLogger(__name__)

_log_archivos = LogArchivosRepository()


def subir_archivo_dashboard(file_storage: FileStorage) -> dict:
    """
    Lee el archivo, calcula SHA-256 hex, rechaza si el hash existe en log_archivos
    y sube el blob al prefijo configurado.

    Returns:
        dict con blob_path, hash (hex), nombre_archivo (nombre seguro).
    """
    data = file_storage.read()
    hash_hex = hashlib.sha256(data).hexdigest()

    with db.get_connection() as conn:
        if _log_archivos.existe_hash(conn, hash_hex):
            logger.info("Rechazo de subida: hash ya presente en log_archivos.")
            raise ArchivoDuplicadoError(hash_hex)

    raw_name = file_storage.filename or "archivo"
    safe = secure_filename(raw_name) or "archivo"
    prefix = (Config.AZURE_BLOB_PREFIX_UPLOAD or "").strip()

    blob_path = subir_bytes(safe, data, prefix)
    return {
        "blob_path": blob_path,
        "hash": hash_hex,
        "nombre_archivo": safe,
    }
