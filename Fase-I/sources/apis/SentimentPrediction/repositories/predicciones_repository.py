from psycopg2.extras import RealDictCursor, execute_values

from db import get_connection


class PrediccionesSentimientoRepository:
    def existe_alguna_para_archivo(self, archivo_id: int) -> bool:
        sql = """
            SELECT 1
            FROM predicciones_sentimiento ps
            INNER JOIN reviews r ON r.id = ps.review_id
            WHERE r.archivo_id = %s
            LIMIT 1
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (archivo_id,))
                return cur.fetchone() is not None

    def contar_por_archivo(self, archivo_id: int) -> dict:
        """
        Totales agregados de predicciones por archivo (sin listar reviews).
        """
        sql = """
            SELECT COUNT(*)::bigint AS total,
                   COUNT(*) FILTER (WHERE ps.sentimiento = 'positivo')::bigint AS positivas,
                   COUNT(*) FILTER (WHERE ps.sentimiento = 'negativo')::bigint AS negativas,
                   COUNT(*) FILTER (WHERE ps.sentimiento = 'neutro')::bigint AS neutras,
                   MAX(ps.modelo_version) AS modelo_version
            FROM predicciones_sentimiento ps
            INNER JOIN reviews r ON r.id = ps.review_id
            WHERE r.archivo_id = %s
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (archivo_id,))
                row = cur.fetchone()
                return dict(row) if row else {}

    def upsert_lote(
        self,
        filas: list[tuple[int, str, float, float, float, float, str]],
        conn,
    ) -> None:
        """
        filas: (review_id, sentimiento, confianza, prob_negativo, prob_neutro, prob_positivo, modelo_version)
        """
        if not filas:
            return
        sql = """
            INSERT INTO predicciones_sentimiento (
                review_id, sentimiento, confianza,
                prob_negativo, prob_neutro, prob_positivo,
                modelo_version
            )
            VALUES %s
            ON CONFLICT (review_id) DO UPDATE SET
                sentimiento = EXCLUDED.sentimiento,
                confianza = EXCLUDED.confianza,
                prob_negativo = EXCLUDED.prob_negativo,
                prob_neutro = EXCLUDED.prob_neutro,
                prob_positivo = EXCLUDED.prob_positivo,
                modelo_version = EXCLUDED.modelo_version,
                procesado_en = NOW()
        """
        with conn.cursor() as cur:
            execute_values(cur, sql, filas)
