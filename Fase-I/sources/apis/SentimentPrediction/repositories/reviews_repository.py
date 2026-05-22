from psycopg2.extras import RealDictCursor

from db import get_connection


class ReviewsRepository:
    def listar_por_archivo(self, archivo_id: int) -> list[dict]:
        sql = """
            SELECT id, texto_limpio
            FROM reviews
            WHERE archivo_id = %s
            ORDER BY id
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (archivo_id,))
                return [dict(row) for row in cur.fetchall()]
