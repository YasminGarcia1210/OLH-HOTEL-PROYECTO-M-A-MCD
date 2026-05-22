"""Validación de bodies para el servicio Sentiment Prediction."""

from config import Config


def validar_body_archivo_id(body: dict) -> list[str]:
    """
    Valida POST con `archivo_id` (entero positivo).
    Retorna lista de mensajes; vacía si es válido.
    """
    if not isinstance(body, dict) or not body:
        return ["El body de la petición no puede estar vacío"]

    if "archivo_id" not in body:
        return ["El campo 'archivo_id' es requerido"]

    aid = body["archivo_id"]
    if not isinstance(aid, int) or isinstance(aid, bool):
        return ["archivo_id debe ser un entero positivo"]
    if aid < 1:
        return ["archivo_id debe ser un entero positivo"]

    return []


def validar_body_texto_review(body: dict) -> list[str]:
    """
    Valida POST con `texto` (string no vacío, longitud acotada).
    Retorna lista de mensajes; vacía si es válido.
    """
    if not isinstance(body, dict) or not body:
        return ["El body de la petición no puede estar vacío"]

    if "texto" not in body:
        return ["El campo 'texto' es requerido"]

    raw = body["texto"]
    if not isinstance(raw, str):
        return ["texto debe ser una cadena de texto"]

    texto = raw.strip()
    if not texto:
        return ["texto no puede estar vacío"]

    if len(texto) > Config.SENTIMENT_MAX_INPUT_CHARS:
        return [
            f"texto excede la longitud máxima permitida ({Config.SENTIMENT_MAX_INPUT_CHARS} caracteres)"
        ]

    return []
