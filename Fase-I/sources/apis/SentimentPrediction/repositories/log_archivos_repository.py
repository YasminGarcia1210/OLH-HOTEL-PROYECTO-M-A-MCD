from psycopg2.extras import RealDictCursor

from db import get_connection


class LogArchivosRepository:
    def buscar_por_id(self, archivo_id: int) -> dict | None:
        sql = """
            SELECT id, estado, etapa_error, mensaje_error, fecha_prediccion
            FROM log_archivos
            WHERE id = %s
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (archivo_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def marcar_predicho(self, archivo_id: int, conn=None) -> None:
        sql = """
            UPDATE log_archivos
            SET estado = 'predicted',
                fecha_prediccion = NOW()
            WHERE id = %s
        """

        def _run(c):
            with c.cursor() as cur:
                cur.execute(sql, (archivo_id,))

        if conn is not None:
            _run(conn)
        else:
            with get_connection() as c:
                _run(c)

    def marcar_error(self, archivo_id: int, etapa: str, mensaje: str, conn=None) -> None:
        sql = """
            UPDATE log_archivos
            SET estado = 'error',
                etapa_error = %s,
                mensaje_error = %s
            WHERE id = %s
        """

        def _run(c):
            with c.cursor() as cur:
                cur.execute(sql, (etapa, mensaje, archivo_id))

        if conn is not None:
            _run(conn)
        else:
            with get_connection() as c:
                _run(c)
