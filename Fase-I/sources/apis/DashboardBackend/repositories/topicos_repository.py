import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_COLS = "id, slug, nombre, tipo, umbral_alerta, activo"


def get_all_topicos(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLS} FROM topicos ORDER BY tipo, nombre"
        )
        return [dict(r) for r in cur.fetchall()]


def update_umbral_alerta(conn, topico_id: int, umbral: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"UPDATE topicos SET umbral_alerta = %s WHERE id = %s RETURNING {_COLS}",
            (umbral, topico_id),
        )
        row = cur.fetchone()
    return dict(row) if row else None
