"""
Servicio principal de ABSA.

Orquesta el flujo completo:
  verificar archivo → cargar tópicos y reviews → analizar → persistir → actualizar estado.
"""

import json
import logging
from datetime import datetime, timezone

from db import get_connection
from lib.slug_utils import to_slug
from models.absa_llm_model import _parsear_respuesta
from models.absa_model_factory import crear_modelo
from repositories.absa_openai_batches_repository import AbsaOpenaiBatchesRepository
from repositories.log_archivos_repository import LogArchivosRepository
from repositories.review_topicos_repository import ReviewTopicosRepository
from repositories.reviews_repository import ReviewsRepository
from repositories.topicos_repository import TopicosRepository
from psycopg2 import IntegrityError as PgIntegrityError

from services.exceptions import (
    ArchivoNoEncontradoError,
    ArchivoYaProcesadoError,
    EstadoInvalidoError,
    LLMError,
    ModeloNoDisponibleError,
    OpenaiBatchJobNoEncontradoError,
    OpenaiBatchPendienteError,
    RespuestaLLMInvalidaError,
)
from services.openai_batch_client import OpenAIBatchABSAClient

logger = logging.getLogger(__name__)

_ESTADO_REQUERIDO = "predicted"
_ESTADO_RESULTADO = "topics_identified"


class ABSAService:

    def __init__(self, config):
        self._config            = config
        self._model             = crear_modelo(config)
        self._log_archivos_repo = LogArchivosRepository()
        self._reviews_repo      = ReviewsRepository()
        self._topicos_repo      = TopicosRepository()
        self._rt_repo           = ReviewTopicosRepository()
        self._batch_repo        = AbsaOpenaiBatchesRepository()
        self._openai_batch_client: OpenAIBatchABSAClient | None = None
        if config.ABSA_MODEL_BACKEND == "llm" and config.LLM_PROVIDER == "openai":
            self._openai_batch_client = OpenAIBatchABSAClient(config)

    def _modelo_version_openai_batch(self) -> str:
        return f"llm-openai-batch-{self._config.OPENAI_MODEL}"

    def _asegurar_cliente_openai_batch(self) -> None:
        if self._openai_batch_client is None:
            raise ModeloNoDisponibleError(
                "OpenAI Batch requiere ABSA_MODEL_BACKEND=llm y LLM_PROVIDER=openai."
            )

    def procesar(self, archivo_id: int) -> dict:
        """
        Ejecuta el pipeline ABSA completo para un archivo.

        Pasos:
          1. Verifica que el archivo existe y está en estado 'predicted'.
          2. Carga los tópicos fijos (tipo='clave') desde BD.
          3. Carga las reviews con su predicción de sentimiento.
          4. Analiza cada review con el modelo configurado.
          5. Persiste tópicos dinámicos nuevos en la tabla topicos.
          6. Inserta en bulk los resultados en review_topicos.
          7. Actualiza log_archivos a estado 'topics_identified'.

        Returns:
            Dict con resumen del procesamiento.

        Lanza:
            ArchivoNoEncontradoError  — archivo_id no existe.
            EstadoInvalidoError       — estado ≠ 'predicted'.
            ArchivoYaProcesadoError   — estado = 'topics_identified'.
            ModeloNoDisponibleError   — backend/proveedor no configurado.
            LLMError / subclases      — fallos de red o autenticación con el LLM.
        """
        with get_connection() as conn:
            # ── 1. Verificar archivo ──────────────────────────────────────────
            archivo = self._log_archivos_repo.buscar_por_id(conn, archivo_id)
            if not archivo:
                raise ArchivoNoEncontradoError(
                    f"No se encontró el archivo con id={archivo_id} en la base de datos."
                )

            estado_actual = archivo["estado"]
            if estado_actual == _ESTADO_RESULTADO:
                raise ArchivoYaProcesadoError(
                    f"El archivo_id {archivo_id} ya tiene tópicos identificados. "
                    f"Estado: {estado_actual}"
                )
            if estado_actual != _ESTADO_REQUERIDO:
                raise EstadoInvalidoError(
                    f"El archivo debe estar en estado '{_ESTADO_REQUERIDO}' para ejecutar ABSA. "
                    f"Estado actual: '{estado_actual}'"
                )

            if self._batch_repo.buscar_pendiente_por_archivo(conn, archivo_id):
                raise OpenaiBatchPendienteError(
                    f"El archivo_id {archivo_id} tiene un batch OpenAI pendiente de sincronizar. "
                    "Use POST /api/v1/absa/batch/sincronizar o espere al poller."
                )

            # ── 2. Cargar tópicos ─────────────────────────────────────────────
            topicos_fijos = self._topicos_repo.listar_clave(conn)
            if not topicos_fijos:
                logger.warning("No hay tópicos de tipo 'clave' activos en la BD.")
            topicos_adicionales = self._topicos_repo.listar_adicionales(conn)

            # ── 3. Cargar reviews con sentimiento ─────────────────────────────
            reviews = self._reviews_repo.listar_por_archivo(conn, archivo_id)
            if not reviews:
                logger.warning("No hay reviews con predicción de sentimiento para archivo_id=%s.", archivo_id)
                self._log_archivos_repo.actualizar_estado_archivo(conn, archivo_id)
                return _construir_resumen(archivo_id, self._model.version, [], {})

            # ── 4 + 5 + 6. Analizar, persistir tópicos dinámicos y acumular ──
            asignaciones, distribucion, tokens_entrada, tokens_salida = self._analizar_reviews(
                conn, reviews, topicos_fijos, topicos_adicionales, archivo_id
            )

            # ── 6. Insertar en bulk ───────────────────────────────────────────
            self._rt_repo.insertar_bulk(conn, asignaciones)

            # ── 7. Actualizar estado ──────────────────────────────────────────
            self._log_archivos_repo.actualizar_estado_archivo(conn, archivo_id)

        logger.info(
            "ABSA completado: archivo_id=%s, reviews=%d, asignaciones=%d.",
            archivo_id, len(reviews), len(asignaciones),
        )
        return _construir_resumen(
            archivo_id, self._model.version, asignaciones, distribucion,
            tokens_entrada, tokens_salida,
        )

    def encolar_procesamiento_batch(self, archivo_id: int) -> dict:
        """
        Crea un trabajo OpenAI Batch (JSONL) para todas las reviews del archivo.

        El archivo debe seguir en estado 'predicted' hasta que se llame a
        sincronizar_batches_pendientes y el batch esté 'completed' en OpenAI.
        """
        self._asegurar_cliente_openai_batch()

        with get_connection() as conn:
            archivo = self._log_archivos_repo.buscar_por_id(conn, archivo_id)
            if not archivo:
                raise ArchivoNoEncontradoError(
                    f"No se encontró el archivo con id={archivo_id} en la base de datos."
                )

            estado_actual = archivo["estado"]
            if estado_actual == _ESTADO_RESULTADO:
                raise ArchivoYaProcesadoError(
                    f"El archivo_id {archivo_id} ya tiene tópicos identificados. "
                    f"Estado: {estado_actual}"
                )
            if estado_actual != _ESTADO_REQUERIDO:
                raise EstadoInvalidoError(
                    f"El archivo debe estar en estado '{_ESTADO_REQUERIDO}' para ejecutar ABSA. "
                    f"Estado actual: '{estado_actual}'"
                )

            if self._batch_repo.buscar_pendiente_por_archivo(conn, archivo_id):
                raise OpenaiBatchPendienteError(
                    f"El archivo_id {archivo_id} ya tiene un batch OpenAI pendiente."
                )

            topicos_fijos = self._topicos_repo.listar_clave(conn)
            topicos_adicionales = self._topicos_repo.listar_adicionales(conn)
            reviews = self._reviews_repo.listar_por_archivo(conn, archivo_id)

            if not reviews:
                logger.warning(
                    "encolar_procesamiento_batch: sin reviews para archivo_id=%s; se marca topics_identified.",
                    archivo_id,
                )
                self._log_archivos_repo.actualizar_estado_archivo(conn, archivo_id)
                return {
                    "archivo_id":         archivo_id,
                    "openai_batch_id":    None,
                    "total_requests":     0,
                    "estado_openai":      None,
                    "mensaje":            "Sin reviews; archivo pasado a topics_identified.",
                }

            lineas = [
                self._openai_batch_client.construir_linea_jsonl(
                    r["review_id"],
                    r["texto_limpio"],
                    topicos_fijos,
                    topicos_adicionales,
                )
                for r in reviews
            ]

            input_file_id, batch_id, estado_openai = (
                self._openai_batch_client.subir_jsonl_y_crear_batch(lineas)
            )

            try:
                self._batch_repo.insertar(
                    conn,
                    archivo_id,
                    batch_id,
                    input_file_id,
                    estado_openai,
                    len(lineas),
                )
            except PgIntegrityError as e:
                if getattr(e, "pgcode", None) == "23505":
                    raise OpenaiBatchPendienteError(
                        f"No se pudo registrar el batch: ya existe un trabajo pendiente para archivo_id={archivo_id}."
                    ) from e
                raise

        logger.info(
            "OpenAI Batch encolado: archivo_id=%s batch_id=%s requests=%d",
            archivo_id, batch_id, len(lineas),
        )
        return {
            "archivo_id":      archivo_id,
            "openai_batch_id": batch_id,
            "total_requests":  len(lineas),
            "estado_openai":   estado_openai,
        }

    def sincronizar_batches_pendientes(self, openai_batch_id: str | None = None) -> list[dict]:
        """
        Consulta OpenAI para jobs pendientes y aplica resultados cuando status=completed.

        Args:
            openai_batch_id: Si se informa, solo se procesa ese id (debe estar pendiente).

        Returns:
            Lista de dicts con el resultado por batch inspeccionado.
        """
        self._asegurar_cliente_openai_batch()

        with get_connection() as conn:
            if openai_batch_id:
                job = self._batch_repo.buscar_por_openai_batch_id(conn, openai_batch_id)
                if not job:
                    raise OpenaiBatchJobNoEncontradoError(
                        f"No existe registro para openai_batch_id={openai_batch_id}."
                    )
                if job["estado_aplicacion"] != "pendiente":
                    return [{
                        "openai_batch_id": openai_batch_id,
                        "accion":          "omitido",
                        "motivo":          f"estado_aplicacion={job['estado_aplicacion']}",
                    }]
                jobs = [job]
            else:
                jobs = self._batch_repo.listar_pendientes(conn)

            resultados: list[dict] = []
            for job in jobs:
                resultados.append(
                    self._sincronizar_un_batch(conn, job),
                )
            return resultados

    def _sincronizar_un_batch(self, conn, job: dict) -> dict:
        """Procesa un registro pendiente (misma conexión / transacción)."""
        oid = job["openai_batch_id"]
        archivo_id = job["archivo_id"]

        batch_obj = self._openai_batch_client.obtener_batch(oid)
        status = getattr(batch_obj, "status", None) or "unknown"
        self._batch_repo.actualizar_estado_openai(conn, oid, status)

        if status in ("validating", "in_progress", "finalizing", "cancelling"):
            return {
                "openai_batch_id": oid,
                "archivo_id":      archivo_id,
                "estado_openai":   status,
                "accion":          "esperando",
            }

        if status == "completed":
            output_file_id = getattr(batch_obj, "output_file_id", None)
            if not output_file_id:
                msg = "Batch completed sin output_file_id"
                self._log_archivos_repo.registrar_error(conn, archivo_id, "openai_batch", msg)
                self._batch_repo.marcar_fallido(conn, oid, msg)
                return {
                    "openai_batch_id": oid,
                    "archivo_id":      archivo_id,
                    "accion":          "fallido",
                    "detalle":         msg,
                }

            texto = self._openai_batch_client.descargar_texto_archivo(output_file_id)
            return self._aplicar_salida_batch_openai(conn, job, texto)

        # Estados terminales de error en OpenAI
        err_detail = getattr(batch_obj, "errors", None)
        msg = f"Batch OpenAI en estado terminal '{status}'"
        if err_detail is not None:
            msg = f"{msg}: {err_detail}"

        self._log_archivos_repo.registrar_error(conn, archivo_id, "openai_batch", msg[:500])
        self._batch_repo.marcar_fallido(conn, oid, msg)
        return {
            "openai_batch_id": oid,
            "archivo_id":      archivo_id,
            "estado_openai":   status,
            "accion":          "fallido",
            "detalle":         msg[:500],
        }

    def _aplicar_salida_batch_openai(self, conn, job: dict, texto_jsonl: str) -> dict:
        archivo_id = job["archivo_id"]
        oid = job["openai_batch_id"]
        total_esperado = job["total_requests"]

        topicos_fijos = self._topicos_repo.listar_clave(conn)
        topicos_adicionales = self._topicos_repo.listar_adicionales(conn)
        slugs_esperados = {t["slug"] for t in topicos_fijos}
        topico_id_por_slug = {t["slug"]: t["id"] for t in topicos_fijos}

        asignaciones: list[dict] = []
        distribucion: dict[str, int] = {}
        topicos_dinamicos_cache: dict[str, int] = {}
        mv = self._modelo_version_openai_batch()

        tokens_entrada_total = 0
        tokens_salida_total = 0
        lineas_ok = 0
        lineas_fallidas = 0

        for line in texto_jsonl.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                lineas_fallidas += 1
                continue

            custom_id = data.get("custom_id")
            if custom_id is None:
                lineas_fallidas += 1
                continue
            try:
                review_id = int(custom_id)
            except (TypeError, ValueError):
                lineas_fallidas += 1
                continue

            if data.get("error"):
                logger.warning(
                    "Batch línea error review_id=%s: %s", review_id, data.get("error"),
                )
                lineas_fallidas += 1
                continue

            resp = data.get("response") or {}
            if resp.get("status_code") != 200:
                lineas_fallidas += 1
                continue

            body = resp.get("body")
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    lineas_fallidas += 1
                    continue
            if not isinstance(body, dict):
                lineas_fallidas += 1
                continue

            choices = body.get("choices") or []
            if not choices:
                lineas_fallidas += 1
                continue
            content = (choices[0].get("message") or {}).get("content") or ""
            uso = body.get("usage") or {}
            tokens_entrada_total += int(uso.get("prompt_tokens") or 0)
            tokens_salida_total += int(uso.get("completion_tokens") or 0)

            try:
                resultado = _parsear_respuesta(content, slugs_esperados)
            except RespuestaLLMInvalidaError as e:
                logger.warning("Batch JSON inválido review_id=%s: %s", review_id, e)
                lineas_fallidas += 1
                continue

            resultado.tokens_entrada = int(uso.get("prompt_tokens") or 0)
            resultado.tokens_salida = int(uso.get("completion_tokens") or 0)

            self._acumular_resultado(
                conn,
                resultado,
                review_id,
                topico_id_por_slug,
                topicos_dinamicos_cache,
                asignaciones,
                distribucion,
                modelo_version=mv,
            )
            lineas_ok += 1

        if lineas_ok == 0 and total_esperado > 0:
            msg = (
                f"Ninguna línea del batch pudo aplicarse (fallidas={lineas_fallidas}, "
                f"esperadas≈{total_esperado})."
            )
            self._log_archivos_repo.registrar_error(conn, archivo_id, "openai_batch", msg)
            self._batch_repo.marcar_fallido(conn, oid, msg)
            return {
                "openai_batch_id":    oid,
                "archivo_id":         archivo_id,
                "accion":             "fallido",
                "detalle":            msg,
                "lineas_fallidas":    lineas_fallidas,
            }

        self._rt_repo.insertar_bulk(conn, asignaciones)
        self._log_archivos_repo.actualizar_estado_archivo(conn, archivo_id)
        self._batch_repo.marcar_aplicado(conn, oid)

        logger.info(
            "OpenAI Batch aplicado: archivo_id=%s batch=%s asignaciones=%d fallidas=%d",
            archivo_id, oid, len(asignaciones), lineas_fallidas,
        )
        return {
            "openai_batch_id":         oid,
            "archivo_id":              archivo_id,
            "accion":                  "aplicado",
            "estado":                  _ESTADO_RESULTADO,
            "modelo_version":          mv,
            "total_asignaciones":      len(asignaciones),
            "lineas_ok":               lineas_ok,
            "lineas_fallidas":         lineas_fallidas,
            "tokens_entrada":          tokens_entrada_total,
            "tokens_salida":           tokens_salida_total,
            "distribucion_topicos":    _distribucion_a_lista(distribucion),
        }

    # ── Métodos privados ──────────────────────────────────────────────────────

    def _analizar_reviews(
        self,
        conn,
        reviews: list[dict],
        topicos_fijos: list[dict],
        topicos_adicionales: list[dict],
        archivo_id: int,
    ) -> tuple[list[dict], dict, int, int]:
        """
        Despacha al modo batch (si el modelo lo soporta) o al loop por review.
        Retorna (asignaciones, distribucion, tokens_entrada, tokens_salida).
        """
        if hasattr(self._model, "analizar_batch"):
            return self._analizar_reviews_batch(conn, reviews, topicos_fijos, topicos_adicionales, archivo_id)
        return self._analizar_reviews_loop(conn, reviews, topicos_fijos, topicos_adicionales, archivo_id)

    def _analizar_reviews_loop(
        self,
        conn,
        reviews: list[dict],
        topicos_fijos: list[dict],
        topicos_adicionales: list[dict],
        archivo_id: int,
    ) -> tuple[list[dict], dict, int, int]:
        """
        Itera sobre las reviews una a una. Usado por el backend LLM.
        """
        asignaciones: list[dict] = []
        distribucion: dict[str, int] = {}
        topicos_dinamicos_cache: dict[str, int] = {}
        topico_id_por_slug = {t["slug"]: t["id"] for t in topicos_fijos}
        total = len(reviews)
        tokens_entrada_total = 0
        tokens_salida_total  = 0

        for idx, review in enumerate(reviews, start=1):
            review_id = review["review_id"]
            texto     = review["texto_limpio"]

            if idx % 50 == 0 or idx == total:
                logger.info(
                    "Analizando reviews: %d/%d (archivo_id=%s).", idx, total, archivo_id
                )

            try:
                resultado = self._model.analizar(texto, topicos_fijos, topicos_adicionales)
            except RespuestaLLMInvalidaError as e:
                logger.error(
                    "review_id=%s omitida por JSON inválido del LLM: %s", review_id, e
                )
                continue
            except LLMError as e:
                logger.error("Error de LLM al procesar review_id=%s: %s", review_id, e)
                raise

            tokens_entrada_total += resultado.tokens_entrada
            tokens_salida_total  += resultado.tokens_salida

            if resultado.topicos_dinamicos:
                logger.info(
                    "review_id=%s: %d tópico(s) dinámico(s) detectados por el LLM: %s",
                    review_id,
                    len(resultado.topicos_dinamicos),
                    [td.nombre for td in resultado.topicos_dinamicos],
                )

            self._acumular_resultado(
                conn,
                resultado,
                review_id,
                topico_id_por_slug,
                topicos_dinamicos_cache,
                asignaciones,
                distribucion,
            )

        return asignaciones, distribucion, tokens_entrada_total, tokens_salida_total

    def _analizar_reviews_batch(
        self,
        conn,
        reviews: list[dict],
        topicos_fijos: list[dict],
        topicos_adicionales: list[dict],
        archivo_id: int,
    ) -> tuple[list[dict], dict, int, int]:
        """
        Procesa todas las reviews en una sola llamada batch. Usado por el backend hybrid.
        """
        asignaciones: list[dict] = []
        distribucion: dict[str, int] = {}
        topicos_dinamicos_cache: dict[str, int] = {}
        topico_id_por_slug = {t["slug"]: t["id"] for t in topicos_fijos}

        logger.info(
            "Ejecutando análisis batch: %d reviews (archivo_id=%s).",
            len(reviews), archivo_id,
        )
        resultados = self._model.analizar_batch(reviews, topicos_fijos, topicos_adicionales)

        total_dinamicos = sum(len(r.topicos_dinamicos) for r in resultados)
        logger.info("analizar_batch completado: %d tópicos dinámicos encontrados en total.", total_dinamicos)

        for review, resultado in zip(reviews, resultados):
            self._acumular_resultado(
                conn,
                resultado,
                review["review_id"],
                topico_id_por_slug,
                topicos_dinamicos_cache,
                asignaciones,
                distribucion,
            )

        return asignaciones, distribucion, 0, 0

    def _acumular_resultado(
        self,
        conn,
        resultado,
        review_id: int,
        topico_id_por_slug: dict,
        topicos_dinamicos_cache: dict,
        asignaciones: list,
        distribucion: dict,
        modelo_version: str | None = None,
    ) -> None:
        """Traduce un ABSAResultado a filas de asignaciones y actualiza la distribución."""
        version = modelo_version if modelo_version is not None else self._model.version
        for tf in resultado.topicos_fijos:
            if not tf.mencionado:
                continue
            topico_id = topico_id_por_slug.get(tf.slug)
            if topico_id is None:
                continue
            asignaciones.append({
                "review_id":      review_id,
                "topico_id":      topico_id,
                "score_topico":   tf.score_topico,
                "fragmento":      tf.fragmento,
                "sentimiento":    tf.sentimiento,
                "modelo_version": version,
            })
            distribucion[tf.slug] = distribucion.get(tf.slug, 0) + 1

        for td in resultado.topicos_dinamicos:
            slug = td.slug if td.slug else to_slug(td.nombre)
            if not slug:
                continue
            if slug in topico_id_por_slug:
                logger.info(
                    "Tópico dinámico '%s' omitido: slug '%s' ya es un tópico clave.",
                    td.nombre, slug,
                )
                continue
            if slug not in topicos_dinamicos_cache:
                try:
                    with conn.cursor() as _cur:
                        _cur.execute("SAVEPOINT sp_td")
                    topico_id = self._topicos_repo.upsert_adicional(conn, slug, td.nombre)
                    with conn.cursor() as _cur:
                        _cur.execute("RELEASE SAVEPOINT sp_td")
                    topicos_dinamicos_cache[slug] = topico_id
                except Exception as e:
                    with conn.cursor() as _cur:
                        _cur.execute("ROLLBACK TO SAVEPOINT sp_td")
                    logger.error(
                        "Error al persistir tópico dinámico '%s' (slug='%s'): %s",
                        td.nombre, slug, e,
                    )
                    continue
            topico_id = topicos_dinamicos_cache[slug]
            asignaciones.append({
                "review_id":      review_id,
                "topico_id":      topico_id,
                "score_topico":   td.score_topico,
                "fragmento":      td.fragmento,
                "sentimiento":    td.sentimiento,
                "modelo_version": version,
            })
            distribucion[slug] = distribucion.get(slug, 0) + 1


# ── Helpers ───────────────────────────────────────────────────────────────────

def _distribucion_a_lista(distribucion: dict) -> list[dict]:
    return sorted(
        [{"slug": slug, "menciones": count} for slug, count in distribucion.items()],
        key=lambda x: -x["menciones"],
    )


def _construir_resumen(
    archivo_id: int,
    modelo_version: str,
    asignaciones: list[dict],
    distribucion: dict,
    tokens_entrada: int = 0,
    tokens_salida: int = 0,
) -> dict:
    distribucion_lista = _distribucion_a_lista(distribucion)
    return {
        "archivo_id":               archivo_id,
        "estado":                   _ESTADO_RESULTADO,
        "modelo_version":           modelo_version,
        "total_reviews_procesadas": len({a["review_id"] for a in asignaciones}),
        "total_asignaciones":       len(asignaciones),
        "distribucion_topicos":     distribucion_lista,
        "tokens_entrada":           tokens_entrada,
        "tokens_salida":            tokens_salida,
        "fecha_topicos":            datetime.now(timezone.utc).isoformat(),
    }
