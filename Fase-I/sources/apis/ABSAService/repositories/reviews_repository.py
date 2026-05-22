"""
Repositorio para la tabla reviews (lectura).

Carga las reviews de un archivo junto con su predicción de sentimiento,
que es el input principal del pipeline ABSA.
"""

import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ReviewsRepository:

    def listar_por_archivo(self, conn, archivo_id: int) -> list[dict]:
        """
        Retorna todas las reviews de un archivo con su predicción de sentimiento.

        Hace JOIN con predicciones_sentimiento para garantizar que solo se
        procesan reviews que ya tienen sentimiento asignado.

        Columnas retornadas:
            review_id, texto_limpio, sentimiento, confianza, modelo_version
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT r.id          AS review_id,
                       r.texto_limpio,
                       ps.sentimiento,
                       ps.confianza,
                       ps.modelo_version
                FROM   reviews r
                JOIN   predicciones_sentimiento ps ON ps.review_id = r.id
                WHERE  r.archivo_id = %s
                ORDER  BY r.id
                """,
                (archivo_id,),
            )
            rows = cur.fetchall()

        logger.info(
            "reviews cargadas para archivo_id=%s: %d registros.", archivo_id, len(rows)
        )
        return [dict(r) for r in rows]
