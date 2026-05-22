"""
Integración con Azure Blob Storage.

Descarga por ruta de blob, sube CSV a un prefijo virtual y mueve blobs
mediante copia en memoria + borrado del origen (equivalente funcional a
“carpetas” en otros almacenes).
"""

from __future__ import annotations

import io
import logging
import os
import pandas as pd
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from services.exceptions import (
    ArchivoNoEncontradoEnDriveError,
    CredencialesInvalidasError,
    DescargaFallidaError,
    MovimientoFallidoError,
    SubidaFallidaError,
)

logger = logging.getLogger(__name__)


def _normalize_blob_name(name: str) -> str:
    return name.strip().lstrip("/")


def _ensure_trailing_slash_prefix(prefix: str) -> str:
    p = prefix.strip().strip("/")
    if not p:
        return ""
    return f"{p}/"


class AzureBlobService:
    """
    Cliente para un único contenedor configurado por AZURE_STORAGE_CONTAINER.
    Las rutas de blob son relativas a ese contenedor.
    """

    def __init__(self) -> None:
        self._service: BlobServiceClient | None = None

    def _get_service(self) -> BlobServiceClient:
        if self._service is not None:
            return self._service

        conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
        if not conn:
            raise CredencialesInvalidasError(
                "AZURE_STORAGE_CONNECTION_STRING no está definida o está vacía. "
                "Configúrala en el archivo .env."
            )

        try:
            self._service = BlobServiceClient.from_connection_string(conn)
            logger.info("Cliente de Azure Blob Storage inicializado correctamente.")
        except Exception as e:
            raise CredencialesInvalidasError(
                f"Error de autenticación con Azure Blob Storage: {e}"
            ) from e

        return self._service

    def _container_name(self) -> str:
        name = os.getenv("AZURE_STORAGE_CONTAINER", "").strip()
        if not name:
            raise CredencialesInvalidasError(
                "AZURE_STORAGE_CONTAINER no está definido o está vacío."
            )
        return name

    def descargar_archivo(self, blob_path: str) -> io.BytesIO:
        blob_path = _normalize_blob_name(blob_path)
        service = self._get_service()
        container = service.get_container_client(self._container_name())
        blob_client = container.get_blob_client(blob_path)

        try:
            downloader = blob_client.download_blob()
            data = downloader.readall()
            buffer = io.BytesIO(data)
            buffer.seek(0)
            logger.info(
                "Blob '%s' descargado correctamente (%d bytes).",
                blob_path,
                len(data),
            )
            return buffer
        except ResourceNotFoundError as e:
            raise ArchivoNoEncontradoEnDriveError(
                f"El blob '{blob_path}' no existe en el contenedor "
                "o las credenciales no tienen permiso para accederlo."
            ) from e
        except HttpResponseError as e:
            if getattr(e, "status_code", None) in (403, 404):
                raise ArchivoNoEncontradoEnDriveError(
                    f"El blob '{blob_path}' no existe o no es accesible."
                ) from e
            raise DescargaFallidaError(
                f"Error HTTP {e.status_code} al descargar el blob '{blob_path}': {e}"
            ) from e
        except CredencialesInvalidasError:
            raise
        except Exception as e:
            raise DescargaFallidaError(
                f"Error inesperado al descargar el blob '{blob_path}': {e}"
            ) from e

    def subir_csv(
        self,
        nombre_archivo: str,
        df: pd.DataFrame,
        folder_prefix: str,
    ) -> str:
        prefix = _ensure_trailing_slash_prefix(folder_prefix)
        dest_name = _normalize_blob_name(prefix + nombre_archivo)

        service = self._get_service()
        container = service.get_container_client(self._container_name())
        blob_client = container.get_blob_client(dest_name)

        if blob_client.exists():
            raise SubidaFallidaError(
                f"Ya existe un blob en destino; no se sobrescribe: '{dest_name}'."
            )

        try:
            buffer = io.BytesIO()
            df.to_csv(buffer, index=False, encoding="utf-8")
            buffer.seek(0)
            data = buffer.getvalue()

            blob_client.upload_blob(data, overwrite=False)
            logger.info(
                "CSV '%s' subido correctamente como '%s'.",
                nombre_archivo,
                dest_name,
            )
            return dest_name
        except CredencialesInvalidasError:
            raise
        except HttpResponseError as e:
            raise SubidaFallidaError(
                f"Error HTTP {e.status_code} al subir '{dest_name}': {e}"
            ) from e
        except Exception as e:
            raise SubidaFallidaError(
                f"Error inesperado al subir '{dest_name}': {e}"
            ) from e

    def mover_archivo(self, blob_path_origen: str, folder_destino_prefix: str) -> None:
        blob_path_origen = _normalize_blob_name(blob_path_origen)
        dest_prefix = _ensure_trailing_slash_prefix(folder_destino_prefix)
        nombre = os.path.basename(blob_path_origen)
        dest_name = _normalize_blob_name(dest_prefix + nombre)

        service = self._get_service()
        container = service.get_container_client(self._container_name())
        source = container.get_blob_client(blob_path_origen)
        dest = container.get_blob_client(dest_name)

        if dest.exists():
            raise MovimientoFallidoError(
                f"Ya existe un blob en destino; no se sobrescribe: '{dest_name}'."
            )

        try:
            if not source.exists():
                raise ArchivoNoEncontradoEnDriveError(
                    f"No se puede mover el blob '{blob_path_origen}': no existe."
                )

            data = source.download_blob().readall()
            dest.upload_blob(data, overwrite=False)
            source.delete_blob()
            logger.info(
                "Blob '%s' movido a '%s'.",
                blob_path_origen,
                dest_name,
            )
        except ArchivoNoEncontradoEnDriveError:
            raise
        except ResourceNotFoundError as e:
            raise ArchivoNoEncontradoEnDriveError(
                f"No se puede mover el blob '{blob_path_origen}': no existe o sin permisos."
            ) from e
        except HttpResponseError as e:
            if getattr(e, "status_code", None) in (403, 404):
                raise ArchivoNoEncontradoEnDriveError(
                    f"No se puede mover el blob '{blob_path_origen}': no existe o sin permisos."
                ) from e
            raise MovimientoFallidoError(
                f"Error HTTP {e.status_code} al mover el blob '{blob_path_origen}': {e}"
            ) from e
        except MovimientoFallidoError:
            raise
        except CredencialesInvalidasError:
            raise
        except Exception as e:
            raise MovimientoFallidoError(
                f"Error inesperado al mover el blob '{blob_path_origen}': {e}"
            ) from e
