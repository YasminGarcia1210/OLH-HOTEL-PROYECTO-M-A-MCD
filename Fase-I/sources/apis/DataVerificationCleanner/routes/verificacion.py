import hashlib
import logging

import os

import yaml
from flask import Blueprint, jsonify, request
import psycopg2

from db import get_connection

from repositories.log_archivos_repository import LogArchivosRepository
from repositories.reviews_repository import ReviewsRepository
from routes.validators import validar_body_ejecutar
from services.azure_blob_service import AzureBlobService
from services.csv_validator_service import CsvValidatorService
from services.cleaning_service import CleaningService
from services.exceptions import (
    ArchivoNoEncontradoEnDriveError,
    CredencialesInvalidasError,
    DescargaFallidaError,
    SubidaFallidaError,
    MovimientoFallidoError,
    CsvEstructuraInvalidaError,
    CsvSinDatosError,
    PipelineLimpiezaError,
    PipelineSinResultadosError,
)

logger          = logging.getLogger(__name__)
log_archivos    = LogArchivosRepository()
reviews_repo    = ReviewsRepository()
blob_store      = AzureBlobService()
csv_validator   = CsvValidatorService()
cleaning        = CleaningService()

verificacion_bp = Blueprint("verificacion", __name__, url_prefix="/api/v1/verificacion")


def ok(data):
    """Envelope de respuesta exitosa."""
    return jsonify({"ok": True, "data": data, "error": None})


def error(codigo, mensaje, status=400):
    """Envelope de respuesta de error."""
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/verificacion/ejecutar
#
# Disparado por el Scheduler. Descarga el CSV desde Azure Blob, valida estructura,
# ejecuta el pipeline de limpieza, opcionalmente sube el CSV limpio y mueve el
# original a otro prefijo. Vuelca las reviews en la BD y registra log_archivos.
#
# Body esperado:
#   drive_id_origen = ruta del blob dentro del contenedor (ej. entrada/reviews.csv)
#   { "hotel_id": 1, "drive_id_origen": "...", "nombre_archivo_origen": "...", "plataforma": "..." }
# ──────────────────────────────────────────────────────────────────────────────
@verificacion_bp.route("/ejecutar", methods=["POST"])
def ejecutar():
    body = request.get_json(silent=True)

    # ── Validación de campos requeridos ───────────────────────
    errores = validar_body_ejecutar(body or {})
    if errores:
        return error(
            codigo="BODY_INVALIDO",
            mensaje="; ".join(errores),
            status=400
        )

    nombre_archivo = body["nombre_archivo_origen"]

    # ── Verificar si el archivo ya fue procesado ───────────────
    try:
        registro = log_archivos.buscar_por_nombre(nombre_archivo)
    except psycopg2.Error as e:
        logger.error("Error al consultar log_archivos: %s", e)
        return error("ERROR_INTERNO", "No se pudo verificar el estado del archivo en la base de datos", 500)

    if registro is not None and registro["estado"] != "error":
        return error(
            codigo="ARCHIVO_YA_PROCESADO",
            mensaje=f"El archivo '{nombre_archivo}' ya fue procesado. Estado actual: {registro['estado']}",
            status=409
        )

    # ── Descargar archivo desde Azure Blob ────────────────────
    try:
        contenido_csv = blob_store.descargar_archivo(body["drive_id_origen"])
    except ArchivoNoEncontradoEnDriveError as e:
        logger.warning("Blob no encontrado: %s", e)
        return error("ARCHIVO_NO_ENCONTRADO_EN_DRIVE", str(e), 404)
    except CredencialesInvalidasError as e:
        logger.error("Credenciales de Azure Blob inválidas: %s", e)
        return error("CREDENCIALES_DRIVE_INVALIDAS", str(e), 503)
    except DescargaFallidaError as e:
        logger.error("Fallo al descargar desde Azure Blob: %s", e)
        return error("ERROR_DESCARGA_DRIVE", str(e), 502)

    hash_archivo = hashlib.sha256(contenido_csv.getvalue()).hexdigest()

    # ── Validar estructura y contenido del CSV ────────────────
    try:
        resultado = csv_validator.validar(contenido_csv)
    except CsvEstructuraInvalidaError as e:
        logger.warning("Estructura del CSV inválida: %s", e)
        return error("ESTRUCTURA_INVALIDA", str(e), 422)
    except CsvSinDatosError as e:
        logger.warning("CSV sin datos utilizables: %s", e)
        return error("CSV_SIN_DATOS", str(e), 422)

    logger.info(
        "CSV '%s' validado: %d total, %d válidas, %d descartadas.",
        nombre_archivo, resultado.total, resultado.validas, resultado.descartadas
    )

    # ── Ejecutar pipeline de limpieza ────────────────────────
    try:
        limpieza = cleaning.limpiar(resultado.df)
    except PipelineSinResultadosError as e:
        logger.warning("Pipeline no produjo resultados: %s", e)
        return error("PIPELINE_SIN_RESULTADOS", str(e), 422)
    except PipelineLimpiezaError as e:
        logger.error("Error en pipeline de limpieza: %s", e)
        return error("ERROR_PIPELINE_LIMPIEZA", str(e), 500)

    logger.info(
        "Limpieza completada: %d → %d filas (%d descartadas).",
        limpieza.total_entrada, limpieza.total_salida, limpieza.descartadas
    )

    nombre_limpio     = _nombre_limpio(nombre_archivo)
    prefix_limpios    = os.getenv("AZURE_BLOB_PREFIX_LIMPIOS", "")
    prefix_procesados = os.getenv("AZURE_BLOB_PREFIX_PROCESADOS", "")

    # ── Persistir: log_archivos + reviews (transacción atómica) ──
    # Primero BD: si falla hace rollback sin haber tocado el almacenamiento.
    # Una única conexión garantiza que ambos inserts sean atómicos.
    try:
        with get_connection() as conn:
            archivo_id = log_archivos.crear(
                datos={
                    "hotel_id":              body["hotel_id"],
                    "nombre_archivo_origen": nombre_archivo,
                    "drive_id_origen":       body["drive_id_origen"],
                    "nombre_archivo_limpio": nombre_limpio,
                    "total_registros":       resultado.total,
                    "registros_validos":     limpieza.total_salida,
                    "registros_descartados": resultado.descartadas + limpieza.descartadas,
                    "estado":                "cleaned",
                    "hash":                  hash_archivo,
                },
                conn=conn,
            )
            n_reviews = reviews_repo.insertar_bulk(
                hotel_id=body["hotel_id"],
                archivo_id=archivo_id,
                df=limpieza.df,
                conn=conn,
                plataforma=body["plataforma"].strip(),
            )

        logger.info(
            "Persistencia completada: log_archivos id=%d, reviews insertadas=%d.",
            archivo_id, n_reviews
        )

    except psycopg2.Error as e:
        logger.error("Error al persistir en BD: %s", e)
        return error("ERROR_PERSISTENCIA", "No se pudo guardar el resultado en la base de datos.", 500)

    # ── Subir CSV limpio y mover original (controlado por pipeline.yaml) ──
    # BD ya confirmada. Los errores de almacenamiento no deshacen la BD.
    ops             = _cargar_operaciones()
    drive_id_limpio = ""

    if ops.get("subir_csv_limpio"):
        if prefix_limpios:
            try:
                drive_id_limpio = blob_store.subir_csv(
                    nombre_limpio, limpieza.df, prefix_limpios
                )
            except SubidaFallidaError as e:
                logger.error("Error al subir CSV limpio a Azure Blob: %s", e)
                return error("ERROR_SUBIDA_DRIVE", str(e), 502)
            except CredencialesInvalidasError as e:
                logger.error("Credenciales inválidas al subir: %s", e)
                return error("CREDENCIALES_DRIVE_INVALIDAS", str(e), 503)
        else:
            logger.warning(
                "subir_csv_limpio=true pero AZURE_BLOB_PREFIX_LIMPIOS no configurado."
            )
    else:
        logger.info("Subida de CSV limpio desactivada (operaciones.subir_csv_limpio=false).")

    if ops.get("mover_archivo_original"):
        if prefix_procesados:
            try:
                blob_store.mover_archivo(body["drive_id_origen"], prefix_procesados)
            except MovimientoFallidoError as e:
                logger.error("Error al mover el archivo original a procesados: %s", e)
                return error("ERROR_MOVER_DRIVE", str(e), 502)
            except ArchivoNoEncontradoEnDriveError as e:
                logger.warning("No se pudo mover el original (no encontrado): %s", e)
        else:
            logger.warning(
                "mover_archivo_original=true pero AZURE_BLOB_PREFIX_PROCESADOS no configurado."
            )
    else:
        logger.info("Movimiento de archivo original desactivado (operaciones.mover_archivo_original=false).")

    return ok({
        "archivo_id":            archivo_id,
        "nombre_archivo_origen": nombre_archivo,
        "nombre_archivo_limpio": nombre_limpio,
        "drive_id_limpio":       drive_id_limpio,
        "hash":                  hash_archivo,
        "estado":                "cleaned",
        "total_registros":       resultado.total,
        "registros_validos":     limpieza.total_salida,
        "registros_descartados": resultado.descartadas + limpieza.descartadas,
    })


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/verificacion/archivos/<archivo_id>
#
# Devuelve el estado y metadatos de un archivo específico en el pipeline.
# Usada por Sentiment Prediction, Topic Identification y Metric Calculation.
# ──────────────────────────────────────────────────────────────────────────────
@verificacion_bp.route("/archivos/<int:archivo_id>", methods=["GET"])
def get_archivo(archivo_id):
    # TODO: consultar log_archivos WHERE id = archivo_id (→ 404 si no existe)

    return ok({
        "archivo_id": archivo_id,
        "hotel_id": 0,
        "nombre_archivo_origen": "",
        "nombre_archivo_limpio": "",
        "drive_id_limpio": "",
        "estado": "",
        "total_registros": 0,
        "registros_validos": 0,
        "fecha_limpieza": None
    })


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/verificacion/archivos
#
# Lista archivos filtrados por hotel_id y/o estado del pipeline.
# Usada por Sentiment Prediction para descubrir archivos listos para procesar.
#
# Query params: hotel_id (int, opcional), estado (string, opcional)
# ──────────────────────────────────────────────────────────────────────────────
@verificacion_bp.route("/archivos", methods=["GET"])
def listar_archivos():
    hotel_id = request.args.get("hotel_id", type=int)
    estado   = request.args.get("estado", type=str)

    # TODO: construir query sobre log_archivos con los filtros recibidos
    # TODO: retornar lista de archivos que coincidan

    return ok([])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nombre_limpio(nombre_origen: str) -> str:
    """
    Genera el nombre del archivo CSV limpio a partir del nombre del archivo origen.
    Ejemplo: 'reviews_hotel_nov2025.csv' -> 'reviews_hotel_nov2025_clean.csv'
    """
    base, _ = os.path.splitext(nombre_origen)
    return f"{base}_clean.csv"


def _cargar_operaciones() -> dict:
    """
    Carga las flags de operaciones post-limpieza desde config/pipeline.yaml.
    Si el archivo no existe o falta la sección, retorna todo desactivado.
    """
    _defaults = {"subir_csv_limpio": False, "mover_archivo_original": False}
    ruta = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "config", "pipeline.yaml")
    )
    try:
        with open(ruta, encoding="utf-8") as f:
            contenido = yaml.safe_load(f)
        return contenido.get("operaciones", _defaults)
    except Exception:
        return _defaults
