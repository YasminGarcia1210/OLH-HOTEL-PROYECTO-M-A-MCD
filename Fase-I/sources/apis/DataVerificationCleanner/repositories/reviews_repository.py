"""
Repositorio para la tabla reviews.

Toda interacción con la tabla reviews pasa por esta clase.

Patrón de conexión:
  Los métodos de escritura aceptan un parámetro opcional conn.
  · Si conn=None  → gestiona su propia transacción.
  · Si conn!=None → usa la conexión del llamador (transacción compartida).
  Esto permite que el insert de reviews y el de log_archivos compartan
  una única transacción atómica: si uno falla, ambos se revierten.
"""

import logging

import pandas as pd
from psycopg2.extras import execute_values

from db import get_connection

logger = logging.getLogger(__name__)


class ReviewsRepository:

    def insertar_bulk(
        self,
        hotel_id: int,
        archivo_id: int,
        df: pd.DataFrame,
        conn=None,
        plataforma: str | None = None,
    ) -> int:
        """
        Inserta en bloque todas las reviews del DataFrame limpio.

        Columnas requeridas en df:
            review      → se guarda en texto_limpio
            fecha       → se guarda en fecha_review (DATE)
        Columnas opcionales en df:
            idioma      → se guarda en idioma (CHAR(5)); default 'es'
            plataforma  → se guarda en plataforma (VARCHAR); default NULL

        Si se pasa el argumento ``plataforma``, se usa ese valor en todas las
        filas (p. ej. desde POST /ejecutar) y tiene prioridad sobre una
        columna homónima en el DataFrame.

        Usa execute_values de psycopg2 para insertar en un único round-trip,
        lo que es significativamente más eficiente que un INSERT por fila.

        Retorna la cantidad de filas insertadas.
        """
        if df.empty:
            logger.warning("DataFrame vacío; no se insertaron reviews.")
            return 0

        filas = _preparar_filas(hotel_id, archivo_id, df, plataforma=plataforma)

        sql = """
            INSERT INTO reviews (
                hotel_id,
                archivo_id,
                plataforma,
                fecha_review,
                texto_limpio,
                idioma
            ) VALUES %s
        """

        def _ejecutar(c):
            with c.cursor() as cur:
                execute_values(cur, sql, filas)
                return len(filas)

        if conn is not None:
            return _ejecutar(conn)
        with get_connection() as c:
            return _ejecutar(c)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _preparar_filas(
    hotel_id: int,
    archivo_id: int,
    df: pd.DataFrame,
    plataforma: str | None = None,
) -> list[tuple]:
    """
    Convierte el DataFrame en una lista de tuplas lista para execute_values.
    Normaliza la columna fecha a datetime.date para PostgreSQL.
    """
    fechas = pd.to_datetime(df["fecha"], format="ISO8601", errors="coerce").dt.date

    filas = []
    for i, row in enumerate(df.itertuples(index=False)):
        plat = (
            plataforma
            if plataforma is not None
            else getattr(row, "plataforma", None)
        )
        filas.append((
            hotel_id,
            archivo_id,
            plat,
            fechas.iloc[i],
            row.review,
            getattr(row, "idioma", "es") or "es",
        ))

    return filas
