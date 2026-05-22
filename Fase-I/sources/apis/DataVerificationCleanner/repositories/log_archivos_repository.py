"""
Repositorio para la tabla log_archivos.

Toda interacción con la tabla log_archivos pasa por esta clase.
La lógica de negocio nunca escribe SQL directamente.

Patrón de conexión:
  - Los métodos de lectura abren su propia conexión (con get_connection()).
  - Los métodos de escritura aceptan un parámetro opcional conn.
    · Si conn=None  → gestiona su propia transacción.
    · Si conn!=None → usa la conexión del llamador (transacción compartida).
    Esto permite coordinar múltiples escrituras en una única transacción atómica.
"""

import logging
from psycopg2.extras import RealDictCursor

from db import get_connection

logger = logging.getLogger(__name__)


class LogArchivosRepository:

    def crear(self, datos: dict, conn=None) -> int:
        """
        Inserta un nuevo registro en log_archivos y retorna el id generado.

        Parámetros esperados en datos:
            hotel_id, nombre_archivo_origen, drive_id_origen, hash,
            total_registros, registros_validos, registros_descartados, estado.
        Campos opcionales: nombre_archivo_limpio, drive_id_limpio.

        Si conn es None, gestiona su propia transacción.
        Si conn es provisto, usa esa conexión (transacción del llamador).
        """
        sql = """
            INSERT INTO log_archivos (
                hotel_id,
                nombre_archivo_origen,
                drive_id_origen,
                nombre_archivo_limpio,
                drive_id_limpio,
                hash,
                total_registros,
                registros_validos,
                registros_descartados,
                estado,
                fecha_limpieza
            ) VALUES (
                %(hotel_id)s,
                %(nombre_archivo_origen)s,
                %(drive_id_origen)s,
                %(nombre_archivo_limpio)s,
                %(drive_id_limpio)s,
                %(hash)s,
                %(total_registros)s,
                %(registros_validos)s,
                %(registros_descartados)s,
                %(estado)s,
                NOW()
            )
            RETURNING id
        """

        def _ejecutar(c):
            with c.cursor() as cur:
                cur.execute(sql, {
                    "hotel_id":               datos["hotel_id"],
                    "nombre_archivo_origen":  datos["nombre_archivo_origen"],
                    "drive_id_origen":        datos.get("drive_id_origen"),
                    "nombre_archivo_limpio":  datos.get("nombre_archivo_limpio"),
                    "drive_id_limpio":        datos.get("drive_id_limpio"),
                    "hash":                   datos["hash"],
                    "total_registros":        datos["total_registros"],
                    "registros_validos":      datos["registros_validos"],
                    "registros_descartados":  datos["registros_descartados"],
                    "estado":                 datos.get("estado", "cleaned"),
                })
                return cur.fetchone()[0]

        if conn is not None:
            return _ejecutar(conn)
        with get_connection() as c:
            return _ejecutar(c)

    def buscar_por_nombre(self, nombre_archivo_origen: str) -> dict | None:
        """
        Busca un registro en log_archivos por el nombre del archivo origen.

        Retorna el registro como dict si existe, None si no se encontró.
        Usado por el endpoint /ejecutar para detectar reprocesamiento.
        """
        sql = """
            SELECT
                id,
                hotel_id,
                nombre_archivo_origen,
                nombre_archivo_limpio,
                drive_id_origen,
                drive_id_limpio,
                hash,
                total_registros,
                registros_validos,
                registros_descartados,
                estado,
                etapa_error,
                mensaje_error,
                fecha_recepcion,
                fecha_limpieza
            FROM log_archivos
            WHERE nombre_archivo_origen = %s
            LIMIT 1
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (nombre_archivo_origen,))
                row = cur.fetchone()
                return dict(row) if row else None

    def buscar_por_id(self, archivo_id: int) -> dict | None:
        """
        Busca un registro en log_archivos por su id primario.

        Retorna el registro como dict si existe, None si no se encontró.
        """
        sql = """
            SELECT
                id,
                hotel_id,
                nombre_archivo_origen,
                nombre_archivo_limpio,
                drive_id_origen,
                drive_id_limpio,
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
            WHERE id = %s
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (archivo_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def listar(self, hotel_id: int | None = None, estado: str | None = None) -> list[dict]:
        """
        Lista registros de log_archivos con filtros opcionales.

        Parámetros:
            hotel_id: filtra por hotel (opcional)
            estado:   filtra por estado del pipeline (opcional)

        Retorna lista de dicts (vacía si no hay resultados).
        """
        condiciones = []
        valores     = []

        if hotel_id is not None:
            condiciones.append("hotel_id = %s")
            valores.append(hotel_id)

        if estado is not None:
            condiciones.append("estado = %s")
            valores.append(estado)

        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

        sql = f"""
            SELECT
                id,
                hotel_id,
                nombre_archivo_limpio,
                estado,
                registros_validos,
                fecha_limpieza
            FROM log_archivos
            {where}
            ORDER BY fecha_recepcion DESC
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, valores)
                return [dict(row) for row in cur.fetchall()]
