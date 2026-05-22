"""
Excepciones de dominio del servicio Data Verification & Cleaner.

La capa de rutas solo captura estas excepciones, nunca las de librerías
externas (psycopg2, azure SDK, etc.). Esto desacopla la lógica de
negocio de los detalles de implementación.
"""


# ── CSV ──────────────────────────────────────────────────────────────────────

class CsvError(Exception):
    """Error base para cualquier fallo al procesar el CSV."""


class CsvEstructuraInvalidaError(CsvError):
    """El CSV no tiene las columnas requeridas o no puede parsearse."""


class CsvSinDatosError(CsvError):
    """El CSV está vacío o no contiene filas con datos válidos."""


# ── Pipeline de limpieza ──────────────────────────────────────────────────────

class PipelineLimpiezaError(Exception):
    """Error base para cualquier fallo durante la ejecución del pipeline de limpieza."""


class PipelineSinResultadosError(PipelineLimpiezaError):
    """El pipeline finalizó pero no quedaron filas válidas tras la limpieza."""


# ── Almacenamiento (Azure Blob) ─────────────────────────────────────────────

class AlmacenamientoError(Exception):
    """Error base para fallos al interactuar con el almacenamiento de blobs."""


# Compatibilidad con código o docs que mencionaban Google Drive
GoogleDriveError = AlmacenamientoError


class ArchivoNoEncontradoEnDriveError(AlmacenamientoError):
    """El blob no existe o no es accesible con las credenciales actuales."""


class CredencialesInvalidasError(AlmacenamientoError):
    """Las credenciales de almacenamiento son inválidas o faltan."""


class DescargaFallidaError(AlmacenamientoError):
    """Error de red o del servicio durante la descarga del archivo."""


class SubidaFallidaError(AlmacenamientoError):
    """Error durante la subida de un archivo al almacenamiento."""


class MovimientoFallidoError(AlmacenamientoError):
    """Error al mover un blob entre prefijos (carpetas virtuales)."""
