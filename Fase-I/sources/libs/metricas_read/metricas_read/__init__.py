"""
Paquete compartido: lecturas de métricas pre-calculadas (PostgreSQL vía `db` del host).

Las funciones de consulta están en `metricas_read.service` (requieren pool `db` inicializado).
"""

from metricas_read.exceptions import MetricasReadError, TopicoNoEncontradoError
from metricas_read.tendencia import tendencia_desde_cambio_pct

__all__ = [
    "MetricasReadError",
    "TopicoNoEncontradoError",
    "tendencia_desde_cambio_pct",
]
