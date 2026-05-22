import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def get_all_hoteles(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, nombre, ciudad, pais FROM hoteles"
            " WHERE activo = TRUE ORDER BY nombre"
        )
        return [dict(r) for r in cur.fetchall()]
