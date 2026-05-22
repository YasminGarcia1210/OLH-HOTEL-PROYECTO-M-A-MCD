"""
Repositorio para la tabla review_topicos.

Persiste los resultados del análisis ABSA: para cada review, los tópicos
detectados (fijos y dinámicos) con su sentimiento, score y fragmento.
"""

import logging

from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)


class ReviewTopicosRepository:

    def insertar_bulk(self, conn, asignaciones: list[dict]) -> int:
        """
        Inserta en bloque todas las asignaciones review ↔ tópico.

        Usa ON CONFLICT DO NOTHING para ser idempotente: si el par
        (review_id, topico_id) ya existe, se omite sin error.

        Args:
            asignaciones: Lista de dicts con keys:
                review_id, topico_id, score_topico,
                fragmento, sentimiento, modelo_version

        Returns:
            Número de filas efectivamente insertadas.
        """
        if not asignaciones:
            logger.warning("insertar_bulk llamado con lista vacía.")
            return 0

        filas = [
            (
                a["review_id"],
                a["topico_id"],
                a.get("score_topico"),
                a.get("fragmento"),
                a.get("sentimiento"),
                a["modelo_version"],
            )
            for a in asignaciones
        ]

        sql = """
            INSERT INTO review_topicos
                (review_id, topico_id, score_topico, fragmento, sentimiento, modelo_version)
            VALUES %s
            ON CONFLICT (review_id, topico_id) DO NOTHING
        """

        with conn.cursor() as cur:
            execute_values(cur, sql, filas)
            insertadas = cur.rowcount

        logger.info(
            "review_topicos: %d asignaciones enviadas, %d insertadas (resto ya existían).",
            len(filas), insertadas if insertadas >= 0 else len(filas),
        )
        return max(insertadas, 0)
