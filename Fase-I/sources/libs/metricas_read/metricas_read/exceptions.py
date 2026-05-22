"""Excepciones de dominio para consultas de métricas (lectura)."""


class MetricasReadError(Exception):
    """Error base para lecturas de métricas."""


class TopicoNoEncontradoError(MetricasReadError):
    """El tópico solicitado no existe en el catálogo."""
