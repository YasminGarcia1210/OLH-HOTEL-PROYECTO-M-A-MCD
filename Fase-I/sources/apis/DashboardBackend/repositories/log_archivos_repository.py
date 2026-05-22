"""
Acceso a la tabla log_archivos para el DashboardBackend.
"""

from psycopg2.extras import RealDictCursor


class LogArchivosRepository:
    def existe_hash(self, conn, hash_hex: str) -> bool:
        """
        Indica si ya existe un registro con el mismo SHA-256 hex (contenido de origen).
        """
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM log_archivos WHERE upper(hash) = upper(%s) LIMIT 1",
                (hash_hex,),
            )
            return cur.fetchone() is not None

    _SELECT_LOG_COLUMNS = """
            SELECT
                id,
                hotel_id,
                nombre_archivo_origen,
                drive_id_origen,
                hash,
                total_registros,
                registros_validos,
                registros_descartados,
                estado,
                etapa_error,
                mensaje_error,
                fecha_recepcion,
                fecha_limpieza,
                fecha_prediccion,
                fecha_topicos,
                fecha_metricas
            FROM log_archivos
    """

    def contar_log_archivos(self, conn) -> int:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM log_archivos")
            row = cur.fetchone()
        return int(row[0]) if row else 0

    def listar_drive_id_origen(self, conn) -> set[str]:
        """
        Todos los drive_id_origen no nulos (para cruzar con blobs sin cargar todas las filas).
        """
        sql = "SELECT drive_id_origen FROM log_archivos WHERE drive_id_origen IS NOT NULL"
        with conn.cursor() as cur:
            cur.execute(sql)
            return {r[0] for r in cur.fetchall() if r[0]}

    def listar_log_archivos_paginado(
        self, conn, offset: int, limit: int
    ) -> list[dict]:
        """
        Filas de log_archivos ordenadas por recepción reciente, con OFFSET/LIMIT.
        """
        sql = (
            self._SELECT_LOG_COLUMNS.strip()
            + """
            ORDER BY fecha_recepcion DESC NULLS LAST, id DESC
            OFFSET %s LIMIT %s
            """
        )
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (offset, limit))
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def nombres_origen_presentes(self, conn, nombres: list[str]) -> set[str]:
        """
        Devuelve el subconjunto de nombres de archivo que ya existen en nombre_archivo_origen.
        """
        if not nombres:
            return set()
        sql = """
            SELECT nombre_archivo_origen
            FROM log_archivos
            WHERE nombre_archivo_origen = ANY(%s)
        """
        with conn.cursor() as cur:
            cur.execute(sql, (nombres,))
            return {r[0] for r in cur.fetchall() if r[0] is not None}
