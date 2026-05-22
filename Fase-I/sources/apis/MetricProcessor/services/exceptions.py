"""
Excepciones de dominio del servicio Metric Processor.

La capa de rutas captura solo estas excepciones y las traduce a HTTP + envelope
de error. Nunca se propagan detalles de psycopg2 u otras librerías al cliente.
"""


# ── Archivo / pipeline ────────────────────────────────────────────────────────

class MetricasError(Exception):
    """Error base para cualquier fallo en el cálculo de métricas."""


class ArchivoNoEncontradoError(MetricasError):
    """El archivo_id no existe en log_archivos o fue eliminado."""


class HotelNoAsignadoError(MetricasError):
    """El archivo existe pero hotel_id es NULL; no puede asignarse el cálculo a ningún hotel."""


class EstadoInvalidoError(MetricasError):
    """
    El archivo no está en el estado requerido para calcular métricas.
    Se espera estado 'topics_identified'; se informa el estado actual al levantar la excepción.
    """


class SinReviewsError(MetricasError):
    """El archivo no tiene reviews asociadas; no hay datos que agregar."""


class PeriodoNoEncontradoError(MetricasError):
    """No existe fila en metricas_globales_mensual para el hotel y período solicitados."""
