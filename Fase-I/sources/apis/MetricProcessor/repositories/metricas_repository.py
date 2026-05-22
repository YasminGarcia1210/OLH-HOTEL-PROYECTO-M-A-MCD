"""
Repositorio de métricas: escrituras y lecturas auxiliares del pipeline de cálculo.

Las lecturas para el dashboard viven en el paquete `metricas_read`.

Scores persistidos usan suavizado bayesiano (ver `services/metricas_reglas.py`);
`obtener_metricas_global_persistida` y `listar_metricas_topicos_persistidas` alimentan
`POST /api/v1/metricas/recalcular`.

Todas las funciones aceptan conn opcional para participar en la misma transacción;
cuando conn es None obtienen una conexión del pool por su cuenta.
"""

import logging
from datetime import date
from decimal import Decimal

from psycopg2.extras import RealDictCursor

import db

logger = logging.getLogger(__name__)


def _exec(conn, fn):
    if conn is not None:
        return fn(conn)
    with db.get_connection() as c:
        return fn(c)


def obtener_fechas_reviews(archivo_id: int, conn=None) -> list[date]:
    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                "SELECT fecha_review FROM reviews WHERE archivo_id = %s",
                (archivo_id,),
            )
            return [row[0] for row in cur.fetchall()]

    return _exec(conn, _run)


def contar_reviews_por_sentimiento(
    hotel_id: int, anio: int, mes: int, conn=None
) -> dict:
    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)                                              AS total,
                    COUNT(*) FILTER (WHERE ps.sentimiento = 'positivo')  AS positivas,
                    COUNT(*) FILTER (WHERE ps.sentimiento = 'negativo')  AS negativas,
                    COUNT(*) FILTER (WHERE ps.sentimiento = 'neutro')    AS neutras
                FROM reviews r
                JOIN predicciones_sentimiento ps ON ps.review_id = r.id
                JOIN log_archivos             la ON la.id = r.archivo_id
                WHERE r.hotel_id = %s
                  AND EXTRACT(YEAR  FROM r.fecha_review) = %s
                  AND EXTRACT(MONTH FROM r.fecha_review) = %s
                  AND la.estado IN ('topics_identified', 'completed')
                """,
                (hotel_id, anio, mes),
            )
            row = cur.fetchone()
            return {
                "total": int(row[0]),
                "positivas": int(row[1]),
                "negativas": int(row[2]),
                "neutras": int(row[3]),
            }

    return _exec(conn, _run)


def obtener_score_global_anterior(
    hotel_id: int, anio: int, mes: int, conn=None
) -> Decimal | None:
    if mes == 1:
        prev_anio, prev_mes = anio - 1, 12
    else:
        prev_anio, prev_mes = anio, mes - 1

    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT score_promedio
                FROM metricas_globales_mensual
                WHERE hotel_id = %s AND anio = %s AND mes = %s
                """,
                (hotel_id, prev_anio, prev_mes),
            )
            row = cur.fetchone()
            return Decimal(str(row[0])) if row else None

    return _exec(conn, _run)


def obtener_score_topico_anterior(
    hotel_id: int, topico_id: int, anio: int, mes: int, conn=None
) -> Decimal | None:
    if mes == 1:
        prev_anio, prev_mes = anio - 1, 12
    else:
        prev_anio, prev_mes = anio, mes - 1

    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT score_promedio
                FROM metricas_topico_mensual
                WHERE hotel_id = %s AND topico_id = %s AND anio = %s AND mes = %s
                """,
                (hotel_id, topico_id, prev_anio, prev_mes),
            )
            row = cur.fetchone()
            return Decimal(str(row[0])) if row else None

    return _exec(conn, _run)


def obtener_metricas_global_persistida(
    hotel_id: int, anio: int, mes: int, conn=None
) -> dict | None:
    """Lee conteos ya materializados en metricas_globales_mensual (p. ej. POST /recalcular)."""

    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    total_reviews,
                    reviews_positivas,
                    reviews_negativas,
                    reviews_neutras
                FROM metricas_globales_mensual
                WHERE hotel_id = %s AND anio = %s AND mes = %s
                """,
                (hotel_id, anio, mes),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "total_reviews": int(row["total_reviews"]),
                "reviews_positivas": int(row["reviews_positivas"]),
                "reviews_negativas": int(row["reviews_negativas"]),
                "reviews_neutras": int(row["reviews_neutras"]),
            }

    return _exec(conn, _run)


def listar_metricas_topicos_persistidas(
    hotel_id: int, anio: int, mes: int, conn=None
) -> list[dict]:
    """Filas de metricas_topico_mensual del período con metadatos de topicos."""

    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    m.topico_id,
                    t.slug,
                    t.nombre,
                    t.umbral_alerta,
                    m.total_menciones,
                    m.menciones_positivas,
                    m.menciones_negativas,
                    m.menciones_neutras
                FROM metricas_topico_mensual m
                JOIN topicos t ON t.id = m.topico_id
                WHERE m.hotel_id = %s
                  AND m.anio = %s
                  AND m.mes = %s
                ORDER BY t.id
                """,
                (hotel_id, anio, mes),
            )
            rows = cur.fetchall()
        return [
            {
                "topico_id": int(row["topico_id"]),
                "slug": row["slug"],
                "nombre": row["nombre"],
                "umbral_alerta": row["umbral_alerta"],
                "total_menciones": int(row["total_menciones"]),
                "menciones_positivas": int(row["menciones_positivas"]),
                "menciones_negativas": int(row["menciones_negativas"]),
                "menciones_neutras": int(row["menciones_neutras"]),
            }
            for row in rows
        ]

    return _exec(conn, _run)


def obtener_topicos_con_menciones(
    hotel_id: int, anio: int, mes: int, conn=None
) -> list[dict]:
    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    t.id          AS topico_id,
                    t.slug,
                    t.nombre,
                    t.umbral_alerta,
                    COUNT(*)                                               AS total_menciones,
                    COUNT(*) FILTER (WHERE rt.sentimiento = 'positivo')   AS menciones_positivas,
                    COUNT(*) FILTER (WHERE rt.sentimiento = 'negativo')   AS menciones_negativas,
                    COUNT(*) FILTER (WHERE rt.sentimiento = 'neutro')     AS menciones_neutras
                FROM review_topicos rt
                JOIN reviews      r  ON r.id  = rt.review_id
                JOIN topicos      t  ON t.id  = rt.topico_id
                JOIN log_archivos la ON la.id = r.archivo_id
                WHERE r.hotel_id = %s
                  AND EXTRACT(YEAR  FROM r.fecha_review) = %s
                  AND EXTRACT(MONTH FROM r.fecha_review) = %s
                  AND la.estado IN ('topics_identified', 'completed')
                GROUP BY t.id, t.slug, t.nombre, t.umbral_alerta
                ORDER BY t.id
                """,
                (hotel_id, anio, mes),
            )
            return [
                {
                    "topico_id": row["topico_id"],
                    "slug": row["slug"],
                    "nombre": row["nombre"],
                    "umbral_alerta": row["umbral_alerta"],
                    "total_menciones": int(row["total_menciones"]),
                    "menciones_positivas": int(row["menciones_positivas"]),
                    "menciones_negativas": int(row["menciones_negativas"]),
                    "menciones_neutras": int(row["menciones_neutras"]),
                }
                for row in cur.fetchall()
            ]

    return _exec(conn, _run)


def upsert_global(
    hotel_id: int,
    anio: int,
    mes: int,
    *,
    total_reviews: int,
    reviews_positivas: int,
    reviews_negativas: int,
    reviews_neutras: int,
    score_promedio: Decimal,
    cambio_pct_vs_anterior: Decimal | None,
    total_alertas: int,
    conn=None,
) -> None:
    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metricas_globales_mensual
                    (hotel_id, anio, mes,
                     total_reviews, reviews_positivas, reviews_negativas, reviews_neutras,
                     score_promedio, cambio_pct_vs_anterior, total_alertas, calculado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (hotel_id, anio, mes) DO UPDATE SET
                    total_reviews           = EXCLUDED.total_reviews,
                    reviews_positivas       = EXCLUDED.reviews_positivas,
                    reviews_negativas       = EXCLUDED.reviews_negativas,
                    reviews_neutras         = EXCLUDED.reviews_neutras,
                    score_promedio          = EXCLUDED.score_promedio,
                    cambio_pct_vs_anterior  = EXCLUDED.cambio_pct_vs_anterior,
                    total_alertas           = EXCLUDED.total_alertas,
                    calculado_en            = NOW()
                """,
                (
                    hotel_id, anio, mes,
                    total_reviews, reviews_positivas, reviews_negativas, reviews_neutras,
                    score_promedio, cambio_pct_vs_anterior, total_alertas,
                ),
            )
        logger.debug(
            "upsert_global hotel_id=%s %s-%02d score=%.2f alertas=%s",
            hotel_id, anio, mes, score_promedio, total_alertas,
        )

    _exec(conn, _run)


def upsert_topico(
    hotel_id: int,
    topico_id: int,
    anio: int,
    mes: int,
    *,
    total_menciones: int,
    menciones_positivas: int,
    menciones_negativas: int,
    menciones_neutras: int,
    score_promedio: Decimal,
    cambio_pct_vs_anterior: Decimal | None,
    alerta: bool,
    conn=None,
) -> None:
    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metricas_topico_mensual
                    (hotel_id, topico_id, anio, mes,
                     total_menciones, menciones_positivas, menciones_negativas, menciones_neutras,
                     score_promedio, cambio_pct_vs_anterior, alerta, calculado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (hotel_id, topico_id, anio, mes) DO UPDATE SET
                    total_menciones         = EXCLUDED.total_menciones,
                    menciones_positivas     = EXCLUDED.menciones_positivas,
                    menciones_negativas     = EXCLUDED.menciones_negativas,
                    menciones_neutras       = EXCLUDED.menciones_neutras,
                    score_promedio          = EXCLUDED.score_promedio,
                    cambio_pct_vs_anterior  = EXCLUDED.cambio_pct_vs_anterior,
                    alerta                  = EXCLUDED.alerta,
                    calculado_en            = NOW()
                """,
                (
                    hotel_id, topico_id, anio, mes,
                    total_menciones, menciones_positivas, menciones_negativas, menciones_neutras,
                    score_promedio, cambio_pct_vs_anterior, alerta,
                ),
            )

    _exec(conn, _run)


def eliminar_alertas_no_resueltas(
    hotel_id: int, anio: int, mes: int, conn=None
) -> None:
    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                DELETE FROM alertas
                WHERE hotel_id = %s AND anio = %s AND mes = %s
                  AND resuelta = FALSE
                """,
                (hotel_id, anio, mes),
            )
            count = cur.rowcount
        if count:
            logger.debug(
                "Eliminadas %s alertas no resueltas hotel_id=%s %s-%02d",
                count, hotel_id, anio, mes,
            )

    _exec(conn, _run)


def insertar_alerta(
    hotel_id: int,
    topico_id: int,
    anio: int,
    mes: int,
    *,
    score_actual: Decimal,
    umbral_usado: int,
    conn=None,
) -> None:
    mensaje = f"Score {float(score_actual):.2f}% está por debajo del umbral {umbral_usado}%"

    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alertas
                    (hotel_id, topico_id, anio, mes, score_actual, umbral_usado, mensaje)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (hotel_id, topico_id, anio, mes, score_actual, umbral_usado, mensaje),
            )

    _exec(conn, _run)
