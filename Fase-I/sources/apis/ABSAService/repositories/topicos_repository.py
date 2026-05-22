"""
Repositorio para la tabla topicos.

Operaciones de lectura (tópicos clave) y escritura (tópicos adicionales
descubiertos dinámicamente por el modelo ABSA).
"""

import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class TopicosRepository:

    def listar_clave(self, conn) -> list[dict]:
        """
        Retorna los tópicos de tipo 'clave' que están activos.
        Son los tópicos predefinidos que se evalúan en todas las reviews.

        Columnas retornadas: id, slug, nombre, tipo
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, slug, nombre, tipo
                FROM   topicos
                WHERE  tipo   = 'clave'
                  AND  activo = TRUE
                ORDER  BY id
                """
            )
            rows = cur.fetchall()

        logger.info("Tópicos clave cargados: %d.", len(rows))
        return [dict(r) for r in rows]

    def listar_adicionales(self, conn) -> list[dict]:
        """Retorna los tópicos de tipo 'adicional' activos (slug, nombre)."""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, slug, nombre
                FROM   topicos
                WHERE  tipo   = 'adicional'
                  AND  activo = TRUE
                ORDER  BY id
                """
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def upsert_adicional(self, conn, slug: str, nombre: str) -> int:
        """
        Inserta un tópico adicional (descubierto dinámicamente) si no existe.
        Si ya existe con ese slug, retorna su id sin modificarlo.

        Returns:
            El id del tópico (nuevo o existente).
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO topicos (slug, nombre, tipo, activo)
                VALUES (%s, %s, 'adicional', TRUE)
                ON CONFLICT (slug) DO NOTHING
                RETURNING id
                """,
                (slug, nombre),
            )
            row = cur.fetchone()

            if row:
                topico_id = row[0]
                logger.info("Tópico adicional creado: slug='%s', id=%s.", slug, topico_id)
            else:
                # Ya existía — obtener su id
                cur.execute("SELECT id FROM topicos WHERE slug = %s", (slug,))
                topico_id = cur.fetchone()[0]
                logger.debug("Tópico adicional ya existía: slug='%s', id=%s.", slug, topico_id)

        return topico_id
