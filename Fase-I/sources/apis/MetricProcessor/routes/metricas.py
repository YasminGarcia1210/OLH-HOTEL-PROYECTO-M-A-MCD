import logging

from flask import Blueprint, jsonify, request

from routes.validators import validar_body_calcular, validar_body_recalcular
from services.exceptions import (
    ArchivoNoEncontradoError,
    EstadoInvalidoError,
    HotelNoAsignadoError,
    PeriodoNoEncontradoError,
    SinReviewsError,
)
from services.metricas_service import calcular_metricas, recalcular_periodo

logger = logging.getLogger(__name__)

metricas_bp = Blueprint("metricas", __name__, url_prefix="/api/v1/metricas")


def ok(data):
    """Envelope de respuesta exitosa."""
    return jsonify({"ok": True, "data": data, "error": None})


def error(codigo, mensaje, status=400):
    """Envelope de respuesta de error."""
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/metricas/calcular
#
# Disparado por el Scheduler tras la etapa de identificación de tópicos.
# Calcula y persiste las métricas mensuales en metricas_globales_mensual y
# metricas_topico_mensual. Genera alertas para tópicos bajo umbral.
# Actualiza log_archivos.estado = 'completed'.
#
# Un archivo puede tener reviews en varios meses naturales; el job NO bloquea
# archivos multi-mes: calcula un UPSERT por cada (anio, mes) distinto hallado
# en reviews.fecha_review (estrategia A + C del plan de Fase 0).
#
# Body esperado:
#   { "archivo_id": 12 }
#
# Respuesta (200):
#   { "periodos": [{anio, mes}, ...], "metricas_por_periodo": [...] }
#
# Consumidores: Cloud Scheduler / pipeline interno (no el dashboard web).
# ──────────────────────────────────────────────────────────────────────────────
@metricas_bp.route("/calcular", methods=["POST"])
def calcular():
    body = request.get_json(silent=True)

    errores = validar_body_calcular(body or {})
    if errores:
        return error("BODY_INVALIDO", "; ".join(errores), 400)

    archivo_id = body["archivo_id"]
    logger.info("Calculando métricas para archivo_id=%s", archivo_id)

    try:
        resultado = calcular_metricas(archivo_id)
    except ArchivoNoEncontradoError as exc:
        logger.warning("archivo_id=%s no encontrado: %s", archivo_id, exc)
        return error("ARCHIVO_NO_ENCONTRADO", str(exc), 404)
    except HotelNoAsignadoError as exc:
        logger.warning("Hotel no asignado archivo_id=%s: %s", archivo_id, exc)
        return error("HOTEL_NO_ASIGNADO", str(exc), 422)
    except EstadoInvalidoError as exc:
        logger.warning("Estado inválido archivo_id=%s: %s", archivo_id, exc)
        return error("ESTADO_INVALIDO", str(exc), 409)
    except SinReviewsError as exc:
        logger.warning("Sin reviews archivo_id=%s: %s", archivo_id, exc)
        return error("SIN_REVIEWS", str(exc), 422)
    except Exception as exc:
        logger.error("Error inesperado calculando métricas archivo_id=%s: %s", archivo_id, exc, exc_info=True)
        return error("ERROR_INTERNO", "Error inesperado al calcular métricas", 500)

    return ok(resultado), 200


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/metricas/recalcular
#
# Body: { "hotel_id": 1, "anio": 2025, "mes": 11 }
# Reaplica suavizado bayesiano sobre conteos ya persistidos y reevalúa alertas.
# ──────────────────────────────────────────────────────────────────────────────
@metricas_bp.route("/recalcular", methods=["POST"])
def recalcular():
    body = request.get_json(silent=True)

    errores = validar_body_recalcular(body or {})
    if errores:
        return error("BODY_INVALIDO", "; ".join(errores), 400)

    hotel_id = body["hotel_id"]
    anio = body["anio"]
    mes = body["mes"]

    logger.info("Recalcular métricas hotel_id=%s período=%s-%02d", hotel_id, anio, mes)

    try:
        resultado = recalcular_periodo(hotel_id, anio, mes)
    except PeriodoNoEncontradoError as exc:
        logger.warning("Período no encontrado hotel_id=%s %s-%02d: %s", hotel_id, anio, mes, exc)
        return error("PERIODO_NO_ENCONTRADO", str(exc), 404)
    except Exception as exc:
        logger.error(
            "Error inesperado recalculando métricas hotel_id=%s %s-%02d: %s",
            hotel_id, anio, mes, exc, exc_info=True,
        )
        return error("ERROR_INTERNO", "Error inesperado al recalcular métricas", 500)

    return ok(resultado), 200
