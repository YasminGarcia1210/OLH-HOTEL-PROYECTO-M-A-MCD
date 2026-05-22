"""
Lógica de negocio: encolado asíncrono y job de predicción de sentimiento.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime

from config import Config
from db import get_connection
from repositories.log_archivos_repository import LogArchivosRepository
from repositories.predicciones_repository import PrediccionesSentimientoRepository
from repositories.reviews_repository import ReviewsRepository
from services.exceptions import (
    ArchivoNoEncontradoError,
    ArchivoNoListoError,
    ArchivoYaPredichoError,
)
from services.sentiment_model import load_engine, predict_batch

logger = logging.getLogger(__name__)

_log_repo = LogArchivosRepository()
_reviews_repo = ReviewsRepository()
_pred_repo = PrediccionesSentimientoRepository()


def aceptar_procesamiento_async(archivo_id: int) -> dict:
    row = _log_repo.buscar_por_id(archivo_id)
    if row is None:
        raise ArchivoNoEncontradoError(f"No existe archivo_id={archivo_id} en log_archivos.")

    if row["estado"] == "predicted" or _pred_repo.existe_alguna_para_archivo(archivo_id):
        raise ArchivoYaPredichoError(
            f"El archivo_id {archivo_id} ya tiene predicciones. Estado: {row['estado']}"
        )

    if row["estado"] != "cleaned":
        raise ArchivoNoListoError(
            f"El archivo debe estar en estado 'cleaned' para predecir sentimiento. Estado actual: {row['estado']}"
        )

    job_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=_ejecutar_job_sentimiento,
        args=(job_id, archivo_id),
        daemon=True,
        name=f"sentimiento-job-{archivo_id}",
    )
    thread.start()

    return {
        "job_id": job_id,
        "archivo_id": archivo_id,
        "estado": "encolado",
        "mensaje": "El procesamiento se ejecutará de forma asíncrona.",
    }


def _ejecutar_job_sentimiento(job_id: str, archivo_id: int) -> None:
    modelo_version = Config.SENTIMENT_MODEL_VERSION
    batch_size = Config.SENTIMENT_BATCH_SIZE

    try:
        tokenizer, model, device = load_engine(Config.SENTIMENT_MODEL_DIR, Config.SENTIMENT_DEVICE)
        rows = _reviews_repo.listar_por_archivo(archivo_id)
        if not rows:
            logger.warning(
                "Job sentimiento sin reviews: job_id=%s archivo_id=%s",
                job_id,
                archivo_id,
            )

        todas: list[tuple[int, str, float, float, float, float, str]] = []
        texts_batch: list[str] = []
        ids_batch: list[int] = []

        for row in rows:
            rid = int(row["id"])
            texto = row["texto_limpio"] or ""
            ids_batch.append(rid)
            texts_batch.append(texto)
            if len(texts_batch) >= batch_size:
                pred = predict_batch(tokenizer, model, device, texts_batch)
                for r, (sent, conf, pmap) in zip(ids_batch, pred):
                    todas.append(
                        (
                            r,
                            sent,
                            round(conf, 3),
                            round(pmap["negativo"], 3),
                            round(pmap["neutro"], 3),
                            round(pmap["positivo"], 3),
                            modelo_version,
                        )
                    )
                texts_batch = []
                ids_batch = []

        if texts_batch:
            pred = predict_batch(tokenizer, model, device, texts_batch)
            for r, (sent, conf, pmap) in zip(ids_batch, pred):
                todas.append(
                    (
                        r,
                        sent,
                        round(conf, 3),
                        round(pmap["negativo"], 3),
                        round(pmap["neutro"], 3),
                        round(pmap["positivo"], 3),
                        modelo_version,
                    )
                )

        with get_connection() as conn:
            _pred_repo.upsert_lote(todas, conn)
            _log_repo.marcar_predicho(archivo_id, conn=conn)

        logger.info(
            "Job sentimiento completado: job_id=%s archivo_id=%s predicciones=%s",
            job_id,
            archivo_id,
            len(todas),
        )
    except Exception as ex:
        logger.exception("Fallo job sentimiento job_id=%s archivo_id=%s", job_id, archivo_id)
        try:
            msg = str(ex)[:8000]
            _log_repo.marcar_error(archivo_id, "sentiment_prediction", msg)
        except Exception:
            logger.exception(
                "No se pudo marcar error en log_archivos para archivo_id=%s",
                archivo_id,
            )


def _mapear_estado_proceso(estado_log: str) -> str:
    if estado_log in ("predicted", "topics_identified", "completed"):
        return "completado"
    if estado_log == "error":
        return "fallido"
    if estado_log == "cleaned":
        return "en_proceso"
    return "no_iniciado"


def _serializar_fecha_prediccion(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def obtener_resultados_archivo(archivo_id: int) -> dict:
    log_row = _log_repo.buscar_por_id(archivo_id)
    if log_row is None:
        raise ArchivoNoEncontradoError(f"No existe archivo_id={archivo_id} en log_archivos.")

    estado_log = log_row.get("estado") or ""
    estado_proceso = _mapear_estado_proceso(estado_log)

    counts = _pred_repo.contar_por_archivo(archivo_id)
    total = int(counts.get("total") or 0)
    mv = counts.get("modelo_version")
    modelo_version = (mv or "") if mv is not None else ""

    resumen = {
        "positivas": int(counts.get("positivas") or 0),
        "negativas": int(counts.get("negativas") or 0),
        "neutras": int(counts.get("neutras") or 0),
    }

    if estado_proceso == "fallido":
        etapa_error = log_row.get("etapa_error")
        mensaje_error = log_row.get("mensaje_error")
    else:
        etapa_error = None
        mensaje_error = None

    return {
        "archivo_id": archivo_id,
        "estado_proceso": estado_proceso,
        "modelo_version": modelo_version,
        "total": total,
        "resumen": resumen,
        "fecha_prediccion": _serializar_fecha_prediccion(log_row.get("fecha_prediccion")),
        "etapa_error": etapa_error,
        "mensaje_error": mensaje_error,
    }


def predecir_texto_aislado(texto: str) -> dict:
    """
    Ejecuta el modelo sobre un único texto sin leer ni escribir en BD.
    """
    modelo_version = Config.SENTIMENT_MODEL_VERSION
    tokenizer, model, device = load_engine(Config.SENTIMENT_MODEL_DIR, Config.SENTIMENT_DEVICE)
    pred = predict_batch(tokenizer, model, device, [texto])
    sent, conf, prob_map = pred[0]
    return {
        "sentimiento": sent,
        "confianza": round(conf, 3),
        "probabilidades": {
            "negativo": round(prob_map["negativo"], 3),
            "neutro": round(prob_map["neutro"], 3),
            "positivo": round(prob_map["positivo"], 3),
        },
        "modelo_version": modelo_version,
    }
