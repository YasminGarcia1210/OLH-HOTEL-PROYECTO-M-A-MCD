import logging

import psycopg2
from flask import Blueprint, jsonify, request

from routes.validators import validar_body_archivo_id, validar_body_texto_review
from services import sentimiento_service
from services.exceptions import (
    ArchivoNoEncontradoError,
    ArchivoNoListoError,
    ArchivoYaPredichoError,
)

logger = logging.getLogger(__name__)

sentimiento_bp = Blueprint("sentimiento", __name__, url_prefix="/api/v1/sentimiento")


def ok(data):
    return jsonify({"ok": True, "data": data, "error": None})


def error(codigo, mensaje, status=400):
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/sentimiento/procesar
#
# Encola el trabajo de predicción de sentimiento para un archivo (alto volumen).
# Body: { "archivo_id": <int> }
# Consumidor: Scheduler / pipeline.
# ──────────────────────────────────────────────────────────────────────────────
@sentimiento_bp.route("/procesar", methods=["POST"])
def procesar():
    body = request.get_json(silent=True)
    errores = validar_body_archivo_id(body or {})
    if errores:
        return error("BODY_INVALIDO", "; ".join(errores), 400)

    archivo_id = body["archivo_id"]
    try:
        data = sentimiento_service.aceptar_procesamiento_async(archivo_id)
    except ArchivoNoEncontradoError as ex:
        return error("ARCHIVO_NO_ENCONTRADO", str(ex), 404)
    except ArchivoYaPredichoError as ex:
        return error("ARCHIVO_YA_PREDICHO", str(ex), 409)
    except ArchivoNoListoError as ex:
        return error("ARCHIVO_NO_LISTO", str(ex), 422)
    except psycopg2.Error:
        logger.exception("Error de base de datos en POST /sentimiento/procesar")
        return error("ERROR_INTERNO", "Error al acceder a la base de datos.", 500)

    logger.info(
        "Procesamiento de sentimiento aceptado (async): archivo_id=%s job_id=%s",
        archivo_id,
        data["job_id"],
    )
    return ok(data), 202


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/sentimiento/predecir
#
# Predicción síncrona sobre un texto; no persiste en BD.
# Body: { "texto": "<review en texto plano>" }
# Consumidor: pruebas, demos u otros servicios (etiqueta + softmax por clase).
# ──────────────────────────────────────────────────────────────────────────────
@sentimiento_bp.route("/predecir", methods=["POST"])
def predecir():
    body = request.get_json(silent=True)
    errores = validar_body_texto_review(body or {})
    if errores:
        return error("BODY_INVALIDO", "; ".join(errores), 400)

    texto = body["texto"].strip()
    try:
        data = sentimiento_service.predecir_texto_aislado(texto)
    except Exception:
        logger.exception("Error en POST /sentimiento/predecir")
        return error("ERROR_INTERNO", "Error al ejecutar el modelo de sentimiento.", 500)

    return ok(data), 200


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/sentimiento/archivo/<archivo_id>/resultados
#
# Estado del job asíncrono (estado_proceso), resumen agregado y metadatos; no lista reviews.
# Usada por Topic Identification u orquestadores del pipeline.
# ──────────────────────────────────────────────────────────────────────────────
@sentimiento_bp.route("/archivo/<int:archivo_id>/resultados", methods=["GET"])
def resultados(archivo_id):
    try:
        data = sentimiento_service.obtener_resultados_archivo(archivo_id)
    except ArchivoNoEncontradoError as ex:
        return error("ARCHIVO_NO_ENCONTRADO", str(ex), 404)
    except psycopg2.Error:
        logger.exception("Error de base de datos en GET /sentimiento/archivo/%s/resultados", archivo_id)
        return error("ERROR_INTERNO", "Error al acceder a la base de datos.", 500)

    return ok(data), 200
