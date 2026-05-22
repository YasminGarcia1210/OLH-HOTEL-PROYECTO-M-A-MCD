"""Excepciones de dominio: la capa de rutas las traduce a HTTP + envelope."""


class SentimientoError(Exception):
    """Base para errores de negocio del servicio de sentimiento."""


class ArchivoNoEncontradoError(SentimientoError):
    """No existe fila en log_archivos para el id dado."""


class ArchivoYaPredichoError(SentimientoError):
    """El archivo ya tiene predicciones o estado predicted."""


class ArchivoNoListoError(SentimientoError):
    """El archivo no está en estado cleaned (no puede encolarse aún)."""
