import datetime
import logging

import psycopg2
from flask import Blueprint, jsonify, request
from metricas_read.exceptions import TopicoNoEncontradoError
from metricas_read.service import (
    obtener_alertas,
    obtener_kpis_mensual,
    obtener_sentimiento_mensual,
    obtener_topico_detalle_mensual,
    obtener_topicos_mensual,
    obtener_topicos_top5_mensual,
)

import db
from flask_jwt_extended import jwt_required
from routes.validators import (
    validar_body_recalcular_semestre,
    validar_dashboard_reviews_args,
    validar_query_alertas,
    validar_query_archivos_entrada,
    validar_query_kpis_mensual,
    validar_query_sentimiento_mensual,
    validar_query_topicos_mensual,
    validar_slug_topico,
    validar_upload_archivo,
)
from services import dashboard_reviews_service as reviews_svc
from services.archivo_upload_service import subir_archivo_dashboard
from services.archivos_entrada_service import obtener_estado_archivos_entrada
from services.exceptions import (
    ArchivoDuplicadoError,
    ConfiguracionEntradaError,
    CredencialesAzureError,
    ListadoAzureError,
    MetricProcessorIndisponibleError,
    SubidaAzureError,
)
from services.metricas_recalculo_service import recalcular_semestre

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/metricas")


def ok(data):
    return jsonify({"ok": True, "data": data, "error": None})


def error(codigo, mensaje, status=400):
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/metricas/kpis
#
# Query: hotel_id, anio, mes (requeridos).
# KPIs del header del dashboard.
#
# Consumidores: aplicación web / cliente del dashboard
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/kpis", methods=["GET"])
@jwt_required()
def get_kpis():
    errores = validar_query_kpis_mensual(request.args)
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 400)

    hotel_id = int(request.args["hotel_id"])
    anio = int(request.args["anio"])
    mes = int(request.args["mes"])

    logger.info("KPIs mensuales hotel_id=%s periodo=%s-%02d", hotel_id, anio, mes)

    try:
        resultado = obtener_kpis_mensual(hotel_id, anio, mes)
    except Exception as exc:
        logger.error(
            "Error obteniendo KPIs hotel_id=%s periodo=%s-%02d: %s",
            hotel_id, anio, mes, exc, exc_info=True,
        )
        return error("ERROR_INTERNO", "Error inesperado al obtener KPIs mensuales", 500)

    return ok(resultado), 200


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/metricas/recalcular-semestre
#
# Body: { "hotel_id": 1 }
# Orquesta 6 llamadas a MetricProcessor POST /api/v1/metricas/recalcular (últimos
# 6 meses incl. mes actual, orden cronológico ascendente). Resumen en data.
#
# Consumidores: aplicación web / operación del dashboard
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/recalcular-semestre", methods=["POST"])
@jwt_required()
def post_recalcular_semestre():
    body = request.get_json(silent=True) or {}
    errores = validar_body_recalcular_semestre(body)
    if errores:
        return error("BODY_INVALIDO", "; ".join(errores), 400)

    hotel_id = int(body["hotel_id"])
    logger.info("Recalcular semestre hotel_id=%s", hotel_id)

    try:
        data = recalcular_semestre(hotel_id)
    except MetricProcessorIndisponibleError as exc:
        logger.warning("MetricProcessor indisponible: %s", exc)
        return error("METRIC_PROCESSOR_INDISPONIBLE", str(exc), 503)
    except Exception as exc:
        logger.error("Error en recalcular-semestre: %s", exc, exc_info=True)
        return error("ERROR_INTERNO", "Error inesperado al recalcular el semestre.", 500)

    return ok(data), 200


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/metricas/sentimiento-mensual
#
# Query: hotel_id, meses | desde, hasta (YYYY-MM)
# Serie mensual para el gráfico de línea.
#
# Consumidores: aplicación web / cliente del dashboard
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/sentimiento-mensual", methods=["GET"])
@jwt_required()
def get_sentimiento_mensual():
    errores = validar_query_sentimiento_mensual(request.args)
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 400)

    hotel_id = int(request.args["hotel_id"])
    meses_raw = request.args.get("meses")
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")

    meses = int(meses_raw) if meses_raw is not None else None

    logger.info(
        "Serie mensual hotel_id=%s meses=%s desde=%s hasta=%s",
        hotel_id, meses, desde, hasta,
    )

    try:
        resultado = obtener_sentimiento_mensual(hotel_id, meses=meses, desde=desde, hasta=hasta)
    except Exception as exc:
        logger.error("Error serie mensual hotel_id=%s: %s", hotel_id, exc, exc_info=True)
        return error("ERROR_INTERNO", "Error inesperado al obtener serie mensual", 500)

    return ok(resultado), 200


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/metricas/topicos
#
# Query: hotel_id, anio, mes, tipo?, solo_alertas?
# Métricas por tópico del período.
#
# Consumidores: aplicación web / cliente del dashboard
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/topicos", methods=["GET"])
@jwt_required()
def get_topicos():
    errores = validar_query_topicos_mensual(request.args)
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 400)

    hotel_id = int(request.args["hotel_id"])
    anio = int(request.args["anio"])
    mes = int(request.args["mes"])

    tipo_raw = request.args.get("tipo")
    tipo = None
    if tipo_raw is not None and str(tipo_raw).strip() != "":
        tipo = str(tipo_raw).strip()

    solo_raw = request.args.get("solo_alertas")
    solo_alertas = (
        str(solo_raw).lower() in ("1", "true", "yes")
        if solo_raw is not None and str(solo_raw).strip() != ""
        else False
    )

    logger.info(
        "GET topicos mensual hotel_id=%s %s-%02d tipo=%s solo_alertas=%s",
        hotel_id, anio, mes, tipo, solo_alertas,
    )

    try:
        resultado = obtener_topicos_mensual(
            hotel_id, anio, mes, tipo=tipo, solo_alertas=solo_alertas
        )
    except Exception as exc:
        logger.error(
            "Error listado tópicos hotel_id=%s %s-%02d: %s",
            hotel_id, anio, mes, exc, exc_info=True,
        )
        return error("ERROR_INTERNO", "Error inesperado al obtener métricas por tópico", 500)

    return ok(resultado), 200


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/metricas/topicos/top5
#
# Query: hotel_id, anio, mes
# Top 5 tópicos más críticos (orden menor score).
#
# Consumidores: aplicación web / cliente del dashboard
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/topicos/top5", methods=["GET"])
@jwt_required()
def get_top5():
    errores = validar_query_kpis_mensual(request.args)
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 400)

    hotel_id = int(request.args["hotel_id"])
    anio = int(request.args["anio"])
    mes = int(request.args["mes"])

    logger.info("Top 5 tópicos críticos hotel_id=%s periodo=%s-%02d", hotel_id, anio, mes)

    try:
        resultado = obtener_topicos_top5_mensual(hotel_id, anio, mes)
    except Exception as exc:
        logger.error(
            "Error top 5 tópicos hotel_id=%s periodo=%s-%02d: %s",
            hotel_id, anio, mes, exc, exc_info=True,
        )
        return error("ERROR_INTERNO", "Error inesperado al obtener top 5 de tópicos", 500)

    return ok(resultado), 200


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/metricas/topicos/<slug>/detalle
#
# Query: hotel_id, anio, mes · path: slug
# Detalle de tópico para el modal.
#
# Consumidores: aplicación web / cliente del dashboard
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/topicos/<slug>/detalle", methods=["GET"])
@jwt_required()
def get_topico_detalle(slug):
    errores = []
    errores.extend(validar_slug_topico(slug))
    errores.extend(validar_query_kpis_mensual(request.args))
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 400)

    hotel_id = int(request.args["hotel_id"])
    anio = int(request.args["anio"])
    mes = int(request.args["mes"])

    slug_norm = slug.strip()
    logger.info(
        "Detalle tópico hotel_id=%s slug=%s periodo=%s-%02d",
        hotel_id, slug_norm, anio, mes,
    )

    try:
        resultado = obtener_topico_detalle_mensual(hotel_id, slug_norm, anio, mes)
    except TopicoNoEncontradoError as exc:
        logger.warning(
            "Tópico no encontrado hotel_id=%s slug=%s: %s",
            hotel_id, slug_norm, exc,
        )
        return error("TOPICO_NO_ENCONTRADO", str(exc), 404)
    except Exception as exc:
        logger.error(
            "Error detalle tópico hotel_id=%s slug=%s periodo=%s-%02d: %s",
            hotel_id, slug_norm, anio, mes, exc, exc_info=True,
        )
        return error("ERROR_INTERNO", "Error inesperado al obtener detalle de tópico", 500)

    return ok(resultado), 200


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/metricas/alertas
#
# Query: hotel_id, resuelta?
# Listado de alertas.
#
# Consumidores: aplicación web / cliente del dashboard
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/alertas", methods=["GET"])
@jwt_required()
def get_alertas():
    errores = validar_query_alertas(request.args)
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 400)

    hotel_id = int(request.args["hotel_id"])
    resuelta_raw = request.args.get("resuelta")
    resuelta = (
        str(resuelta_raw).lower() in ("1", "true", "yes")
        if resuelta_raw is not None and str(resuelta_raw).strip() != ""
        else False
    )

    logger.info("Listado alertas hotel_id=%s resuelta=%s", hotel_id, resuelta)

    try:
        resultado = obtener_alertas(hotel_id, resuelta=resuelta)
    except Exception as exc:
        logger.error(
            "Error listado alertas hotel_id=%s resuelta=%s: %s",
            hotel_id, resuelta, exc, exc_info=True,
        )
        return error("ERROR_INTERNO", "Error inesperado al obtener alertas", 500)

    return ok(resultado), 200


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/metricas/reviews
# Query: hotel_id (req) | fecha_desde, fecha_hasta (ISO-8601, opt; default 30d)
#        sentimiento (positivo|negativo|neutro, opt)
#        topico_slug (opt, prevalece sobre topico_id) | topico_id (opt)
#        page (default 1) | page_size (default 20, max 100) | orden (fecha_desc|fecha_asc)
# Reviews Explorer: lista paginada con predicción de sentimiento y tópicos.
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/reviews", methods=["GET"])
@jwt_required()
def get_dashboard_reviews():
    errores = validar_dashboard_reviews_args(request.args)
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 422)

    hotel_id = int(request.args.get("hotel_id"))
    fecha_desde = _parse_date(request.args.get("fecha_desde"))
    fecha_hasta = _parse_date(request.args.get("fecha_hasta"))
    sentimiento = request.args.get("sentimiento")
    topico_slug = request.args.get("topico_slug")
    topico_id = _int_or_none(request.args.get("topico_id"))
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    orden = request.args.get("orden", "fecha_desc")

    try:
        with db.get_connection() as conn:
            data = reviews_svc.get_reviews(
                conn,
                hotel_id=hotel_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                sentimiento=sentimiento,
                topico_slug=topico_slug,
                topico_id=topico_id,
                page=page,
                page_size=page_size,
                orden=orden,
            )
    except psycopg2.Error:
        logger.error("Error de BD en GET /api/v1/metricas/reviews", exc_info=True)
        return error("ERROR_INTERNO", "Error inesperado al consultar las reviews.", 500)
    except Exception:
        logger.error("Error inesperado en GET /api/v1/metricas/reviews", exc_info=True)
        return error("ERROR_INTERNO", "Error inesperado en el servidor.", 500)

    return ok(data)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/metricas/archivos/entrada
#
# Query: limite? (entero opcional, tope al listar blobs en Azure).
#        pipeline_page, pipeline_page_size (paginación log_archivos; default 1 / 20).
#        pendientes_page, pendientes_page_size (paginación blobs pendientes; default 1 / 20).
# Blobs bajo AZURE_BLOB_PREFIX_UPLOAD frente a log_archivos: pendientes de lectura
# vs filas en pipeline bajo el mismo prefijo.
#
# Consumidores: aplicación web / operación del pipeline
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/archivos/entrada", methods=["GET"])
@jwt_required()
def get_archivos_entrada():
    errores = validar_query_archivos_entrada(request.args)
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 400)

    limite_raw = request.args.get("limite")
    limite = None
    if limite_raw is not None and str(limite_raw).strip() != "":
        limite = int(limite_raw)

    pipeline_page = int(request.args.get("pipeline_page", 1))
    pipeline_page_size = int(request.args.get("pipeline_page_size", 20))
    pendientes_page = int(request.args.get("pendientes_page", 1))
    pendientes_page_size = int(request.args.get("pendientes_page_size", 20))

    try:
        data = obtener_estado_archivos_entrada(
            limite=limite,
            pipeline_page=pipeline_page,
            pipeline_page_size=pipeline_page_size,
            pendientes_page=pendientes_page,
            pendientes_page_size=pendientes_page_size,
        )
    except ConfiguracionEntradaError as exc:
        logger.warning("Listado entrada: configuración incompleta: %s", exc)
        return error("CONFIGURACION_INCOMPLETA", str(exc), 400)
    except CredencialesAzureError as exc:
        logger.error("Azure Blob: credenciales inválidas: %s", exc)
        return error("CREDENCIALES_AZURE_INVALIDAS", str(exc), 503)
    except ListadoAzureError as exc:
        logger.error("Azure Blob: error listando blobs: %s", exc, exc_info=True)
        return error("ERROR_LISTADO_AZURE", str(exc), 502)
    except psycopg2.Error:
        logger.error("Error de BD en GET /api/v1/metricas/archivos/entrada", exc_info=True)
        return error("ERROR_INTERNO", "Error inesperado al consultar log_archivos.", 500)
    except Exception as exc:
        logger.error("Error inesperado en listado archivos entrada: %s", exc, exc_info=True)
        return error("ERROR_INTERNO", "Error inesperado al listar archivos de entrada.", 500)

    return ok(data), 200


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/metricas/archivos/upload
#
# Body: multipart/form-data, campo `archivo` (file).
# Sube el archivo a Azure Blob (prefijo AZURE_BLOB_PREFIX_UPLOAD), rechaza si el
# SHA-256 ya existe en log_archivos. No inserta fila en log_archivos.
#
# Consumidores: aplicación web (carga de CSV u otros orígenes hacia el bucket)
# ──────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/archivos/upload", methods=["POST"])
@jwt_required()
def post_archivo_upload():
    f = request.files.get("archivo")
    errores = validar_upload_archivo(f)
    if errores:
        return error("PARAMETROS_INVALIDOS", "; ".join(errores), 400)

    try:
        data = subir_archivo_dashboard(f)
    except ArchivoDuplicadoError as exc:
        logger.warning("Subida rechazada (hash duplicado): %s", exc)
        return error(
            "ARCHIVO_YA_SUBIDO",
            "Ya existe un archivo registrado con el mismo contenido (hash SHA-256).",
            409,
        )
    except CredencialesAzureError as exc:
        logger.error("Azure Blob: credenciales inválidas: %s", exc)
        return error("CREDENCIALES_AZURE_INVALIDAS", str(exc), 503)
    except SubidaAzureError as exc:
        logger.error("Azure Blob: error de subida: %s", exc, exc_info=True)
        return error("ERROR_SUBIDA_AZURE", str(exc), 502)
    except Exception as exc:
        logger.error("Error inesperado en subida de archivo: %s", exc, exc_info=True)
        return error("ERROR_INTERNO", "Error inesperado al procesar la subida.", 500)

    return ok(data), 200


def _parse_date(value: str | None):
    if value is None:
        return None
    return datetime.date.fromisoformat(value)


def _int_or_none(value: str | None):
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
