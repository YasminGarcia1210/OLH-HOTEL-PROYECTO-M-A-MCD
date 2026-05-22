"""Excepciones de dominio para subida de archivos e integración Azure."""


class ArchivoDuplicadoError(Exception):
    """El hash del archivo ya está registrado en log_archivos."""

    def __init__(self, hash_hex: str) -> None:
        self.hash_hex = hash_hex
        super().__init__(f"Ya existe un archivo con el mismo contenido (hash SHA-256).")


class CredencialesAzureError(Exception):
    """Credenciales o configuración de Azure Blob inválida o ausente."""


class SubidaAzureError(Exception):
    """Error al subir el blob a Azure Storage."""


class ListadoAzureError(Exception):
    """Error al listar blobs en Azure Storage."""


class ConfiguracionEntradaError(Exception):
    """Falta configuración requerida para el listado de archivos de entrada (p. ej. prefijo de blob)."""


class MetricProcessorIndisponibleError(Exception):
    """No se pudo contactar a MetricProcessor (timeout o error de red)."""
