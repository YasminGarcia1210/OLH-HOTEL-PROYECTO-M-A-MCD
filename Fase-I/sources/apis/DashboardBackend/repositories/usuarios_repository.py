import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Consulta base: siempre incluye el nombre del hotel vía LEFT JOIN.
# LEFT JOIN para que usuarios sin hotel (acceso global) no queden excluidos.
_SELECT = """
    SELECT
        u.id,
        u.nombre,
        u.username,
        u.hotel_id,
        h.nombre AS hotel_nombre,
        u.rol,
        u.activo,
        u.creado_en
    FROM usuarios u
    LEFT JOIN hoteles h ON h.id = u.hotel_id
"""


def _fetch_by_id(conn, usuario_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"{_SELECT} WHERE u.id = %s", (usuario_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_all_usuarios(
    conn, page: int, page_size: int, hotel_id: int | None = None
) -> tuple[int, list[dict]]:
    offset = (page - 1) * page_size
    if hotel_id is not None:
        filter_params: list = [hotel_id]
        count_sql = "SELECT COUNT(*) AS total FROM usuarios WHERE hotel_id = %s"
        list_sql = f"{_SELECT} WHERE u.hotel_id = %s ORDER BY u.id LIMIT %s OFFSET %s"
        list_params = [hotel_id, page_size, offset]
    else:
        filter_params = []
        count_sql = "SELECT COUNT(*) AS total FROM usuarios"
        list_sql = f"{_SELECT} ORDER BY u.id LIMIT %s OFFSET %s"
        list_params = [page_size, offset]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(count_sql, filter_params)
        total = cur.fetchone()["total"]
        cur.execute(list_sql, list_params)
        return total, [dict(r) for r in cur.fetchall()]


def get_usuario_by_id(conn, usuario_id: int, hotel_id: int | None = None) -> dict | None:
    if hotel_id is not None:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"{_SELECT} WHERE u.id = %s AND u.hotel_id = %s", (usuario_id, hotel_id))
            row = cur.fetchone()
        return dict(row) if row else None
    return _fetch_by_id(conn, usuario_id)


def create_usuario(conn, nombre: str, username: str, password_hash: str, hotel_id: int | None, rol: str = "viewer") -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO usuarios (nombre, username, password_hash, hotel_id, rol)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (nombre, username, password_hash, hotel_id, rol),
        )
        new_id = cur.fetchone()["id"]
    return _fetch_by_id(conn, new_id)


def update_usuario(conn, usuario_id: int, fields: dict, hotel_id: int | None = None) -> dict | None:
    set_clauses = ", ".join(f"{k} = %s" for k in fields)
    params = list(fields.values()) + [usuario_id]
    where = "WHERE id = %s"
    if hotel_id is not None:
        where += " AND hotel_id = %s"
        params.append(hotel_id)
    with conn.cursor() as cur:
        cur.execute(f"UPDATE usuarios SET {set_clauses} {where}", params)
        if cur.rowcount == 0:
            return None
    return _fetch_by_id(conn, usuario_id)


def delete_usuario(conn, usuario_id: int, hotel_id: int | None = None) -> bool:
    where = "WHERE id = %s"
    params: list = [usuario_id]
    if hotel_id is not None:
        where += " AND hotel_id = %s"
        params.append(hotel_id)
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM usuarios {where}", params)
        return cur.rowcount > 0
