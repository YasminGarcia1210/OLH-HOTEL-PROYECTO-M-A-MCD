"""
Acceso a log_archivos: validación de estado previo y actualización al finalizar el job.
"""

import logging
from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor

import db

logger = logging.getLogger(__name__)


def obtener_archivo(archivo_id: int, conn=None):
    """
    Devuelve la fila de log_archivos para el archivo dado.
    Retorna None si no existe.

    Campos relevantes: id, hotel_id, estado.
    """
    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, hotel_id, estado
                FROM log_archivos
                WHERE id = %s
                """,
                (archivo_id,),
            )
            return cur.fetchone()

    if conn is not None:
        return _run(conn)
    with db.get_connection() as c:
        return _run(c)


def marcar_completado(archivo_id: int, conn=None) -> None:
    """
    Actualiza log_archivos.estado = 'completed' y registra fecha_metricas = NOW().
    """
    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                UPDATE log_archivos
                SET estado = 'completed',
                    fecha_metricas = NOW()
                WHERE id = %s
                """,
                (archivo_id,),
            )
        logger.info("archivo_id=%s marcado como completed", archivo_id)

    if conn is not None:
        _run(conn)
    else:
        with db.get_connection() as c:
            _run(c)
