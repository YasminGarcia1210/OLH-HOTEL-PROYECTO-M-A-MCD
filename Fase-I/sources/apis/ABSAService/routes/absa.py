import logging

import psycopg2
from flask import Blueprint, jsonify, request

from routes.validators import validar_body_procesar, validar_body_sincronizar_batch
from services.exceptions import (
    ArchivoNoEncontradoError,
    ArchivoYaProcesadoError,
    EstadoInvalidoError,
    LLMAutenticacionError,
    LLMConexionError,
    LLMError,
    ModeloNoDisponibleError,
    OpenaiBatchJobNoEncontradoError,
    OpenaiBatchPendienteError,
    RespuestaLLMInvalidaError,
)

logger = logging.getLogger(__name__)

absa_bp = Blueprint("absa", __name__, url_prefix="/api/v1/absa")

# El servicio se inyecta desde create_app() para que use la Config cargada.
# Se accede mediante el atributo del blueprint en lugar de importarlo aquí,
# evitando imports circulares con db.
_absa_service = None


def init_service(service):
    """Registra la instancia de ABSAService. Llamar desde create_app()."""
    global _absa_service
    _absa_service = service


def ok(data):
    """Envelope de respuesta exitosa."""
    return jsonify({"ok": True, "data": data, "error": None})


def error(codigo, mensaje, status=400):
    """Envelope de respuesta de error."""
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/absa/procesar
#
# Disparado por el Scheduler tras la etapa de predicción de sentimiento.
# Lee las reviews con sentimiento del archivo indicado, ejecuta ABSA con el
# modelo configurado y persiste los resultados en review_topicos.
# Actualiza log_archivos.estado a 'topicado'.
#
# Body: { "archivo_id": 12 }
# ──────────────────────────────────────────────────────────────────────────────
@absa_bp.route("/procesar", methods=["POST"])
def procesar():
    body = request.get_json(silent=True)

    errores = validar_body_procesar(body or {})
    if errores:
        return error("BODY_INVALIDO", "; ".join(errores), 400)

    archivo_id = body["archivo_id"]

    try:
        resultado = _absa_service.procesar(archivo_id)
        return ok(resultado)

    except ArchivoNoEncontradoError as e:
        logger.warning("Archivo no encontrado: %s", e)
        return error("ARCHIVO_NO_ENCONTRADO", str(e), 404)

    except ArchivoYaProcesadoError as e:
        logger.info("Archivo ya topicado: %s", e)
        return error("ARCHIVO_YA_TOPICADO", str(e), 409)

    except EstadoInvalidoError as e:
        logger.warning("Estado inválido para ABSA: %s", e)
        return error("ESTADO_INVALIDO", str(e), 409)

    except ModeloNoDisponibleError as e:
        logger.error("Modelo no disponible: %s", e)
        return error("MODELO_NO_DISPONIBLE", str(e), 503)

    except LLMAutenticacionError as e:
        logger.error("Credenciales LLM inválidas: %s", e)
        return error("LLM_CREDENCIALES_INVALIDAS", str(e), 503)

    except LLMConexionError as e:
        logger.error("Error de conexión con LLM: %s", e)
        return error("LLM_NO_DISPONIBLE", str(e), 502)

    except RespuestaLLMInvalidaError as e:
        logger.error("Respuesta LLM inválida tras reintentos: %s", e)
        return error("LLM_RESPUESTA_INVALIDA", str(e), 502)

    except OpenaiBatchPendienteError as e:
        logger.warning("Batch OpenAI pendiente: %s", e)
        return error("OPENAI_BATCH_PENDIENTE", str(e), 409)

    except psycopg2.Error as e:
        logger.error("Error de BD al ejecutar ABSA (archivo_id=%s): %s", archivo_id, e)
        return error("ERROR_INTERNO", "Error al acceder a la base de datos.", 500)


# ── OpenAI Batch: encolar (JSONL) y sincronizar cuando OpenAI complete ─────
#
# Tras predicción de sentimiento, usar POST /procesar-batch en lugar de /procesar
# si se desea Batch API (menor coste, mayor latencia). Luego POST /batch/sincronizar
# (cron) o activar OPENAI_BATCH_POLL_ENABLED.
# ──────────────────────────────────────────────────────────────────────────────
@absa_bp.route("/procesar-batch", methods=["POST"])
def procesar_batch():
    body = request.get_json(silent=True)

    errores = validar_body_procesar(body or {})
    if errores:
        return error("BODY_INVALIDO", "; ".join(errores), 400)

    archivo_id = body["archivo_id"]

    try:
        resultado = _absa_service.encolar_procesamiento_batch(archivo_id)
        return ok(resultado)

    except ArchivoNoEncontradoError as e:
        logger.warning("Archivo no encontrado: %s", e)
        return error("ARCHIVO_NO_ENCONTRADO", str(e), 404)

    except ArchivoYaProcesadoError as e:
        logger.info("Archivo ya topicado: %s", e)
        return error("ARCHIVO_YA_TOPICADO", str(e), 409)

    except EstadoInvalidoError as e:
        logger.warning("Estado inválido para ABSA batch: %s", e)
        return error("ESTADO_INVALIDO", str(e), 409)

    except OpenaiBatchPendienteError as e:
        logger.warning("Batch pendiente: %s", e)
        return error("OPENAI_BATCH_PENDIENTE", str(e), 409)

    except ModeloNoDisponibleError as e:
        logger.error("OpenAI Batch no disponible: %s", e)
        return error("MODELO_NO_DISPONIBLE", str(e), 503)

    except LLMAutenticacionError as e:
        logger.error("Credenciales OpenAI inválidas: %s", e)
        return error("LLM_CREDENCIALES_INVALIDAS", str(e), 503)

    except LLMConexionError as e:
        logger.error("Error de conexión con OpenAI: %s", e)
        return error("LLM_NO_DISPONIBLE", str(e), 502)

    except LLMError as e:
        logger.error("Error LLM/OpenAI batch: %s", e)
        return error("LLM_ERROR", str(e), 502)

    except psycopg2.Error as e:
        logger.error("Error de BD al encolar batch (archivo_id=%s): %s", archivo_id, e)
        return error("ERROR_INTERNO", "Error al acceder a la base de datos.", 500)


@absa_bp.route("/batch/sincronizar", methods=["POST"])
def batch_sincronizar():
    body = request.get_json(silent=True)
    errores = validar_body_sincronizar_batch(body if isinstance(body, dict) else None)
    if errores:
        return error("BODY_INVALIDO", "; ".join(errores), 400)

    openai_batch_id = None
    if isinstance(body, dict) and body.get("openai_batch_id"):
        openai_batch_id = str(body["openai_batch_id"]).strip()

    try:
        resultados = _absa_service.sincronizar_batches_pendientes(openai_batch_id)
        return ok({"resultados": resultados})

    except ModeloNoDisponibleError as e:
        logger.error("OpenAI Batch no disponible: %s", e)
        return error("MODELO_NO_DISPONIBLE", str(e), 503)

    except OpenaiBatchJobNoEncontradoError as e:
        logger.warning("%s", e)
        return error("OPENAI_BATCH_NO_ENCONTRADO", str(e), 404)

    except LLMAutenticacionError as e:
        logger.error("Credenciales OpenAI inválidas: %s", e)
        return error("LLM_CREDENCIALES_INVALIDAS", str(e), 503)

    except LLMConexionError as e:
        logger.error("Error de conexión con OpenAI: %s", e)
        return error("LLM_NO_DISPONIBLE", str(e), 502)

    except LLMError as e:
        logger.error("Error LLM/OpenAI batch sync: %s", e)
        return error("LLM_ERROR", str(e), 502)

    except psycopg2.Error as e:
        logger.error("Error de BD al sincronizar batch OpenAI: %s", e)
        return error("ERROR_INTERNO", "Error al acceder a la base de datos.", 500)
