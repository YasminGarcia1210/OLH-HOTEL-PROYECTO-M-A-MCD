"""
Repositorio para la tabla log_archivos.

Operaciones: consulta de estado y actualización a 'topicado'.
"""

import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class LogArchivosRepository:

    def buscar_por_id(self, conn, archivo_id: int) -> dict | None:
        """
        Retorna el registro de log_archivos para el archivo dado,
        o None si no existe.
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, hotel_id, nombre_archivo_origen, estado,
                       fecha_prediccion, fecha_topicos
                FROM   log_archivos
                WHERE  id = %s
                """,
                (archivo_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def actualizar_estado_archivo(self, conn, archivo_id: int) -> None:
        """
        Actualiza el estado a 'topics_identified' y registra la fecha.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE log_archivos
                SET    estado        = 'topics_identified',
                       fecha_topicos = NOW()
                WHERE  id = %s
                """,
                (archivo_id,),
            )
        logger.info("log_archivos id=%s actualizado a 'topics_identified'.", archivo_id)

    def registrar_error(self, conn, archivo_id: int, etapa: str, mensaje: str) -> None:
        """
        Marca el archivo en estado de error con el detalle de la etapa fallida.
        Se llama desde la ruta si el procesamiento ABSA falla a mitad.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE log_archivos
                SET    estado        = 'error',
                       etapa_error   = %s,
                       mensaje_error = %s
                WHERE  id = %s
                """,
                (etapa, mensaje[:500], archivo_id),
            )
        logger.warning("log_archivos id=%s marcado como error (etapa=%s).", archivo_id, etapa)
