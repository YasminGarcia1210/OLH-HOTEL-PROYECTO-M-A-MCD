"""
Repositorio de solo lectura: metricas_globales_mensual, metricas_topico_mensual, alertas.

Requiere que el proceso haya inicializado el módulo `db` del servicio Flask anfitrión
(pool con get_connection), en sys.path como top-level.
"""

from psycopg2.extras import RealDictCursor

import db


def _exec(conn, fn):
    if conn is not None:
        return fn(conn)
    with db.get_connection() as c:
        return fn(c)


def listar_sentimiento_mensual(
    hotel_id: int,
    desde_anio: int,
    desde_mes: int,
    hasta_anio: int,
    hasta_mes: int,
    conn=None,
) -> list[dict]:
    def _run(c):
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT anio, mes, score_promedio, total_reviews
                FROM metricas_globales_mensual
                WHERE hotel_id = %s
                  AND (anio * 100 + mes) BETWEEN (%s * 100 + %s) AND (%s * 100 + %s)
                ORDER BY anio, mes
                """,
                (hotel_id, desde_anio, desde_mes, hasta_anio, hasta_mes),
            )
            return [
                {
                    "anio": row[0],
                    "mes": row[1],
                    "score_promedio": float(row[2]),
                    "total_reviews": int(row[3]),
                }
                for row in cur.fetchall()
            ]

    return _exec(conn, _run)


def obtener_kpis_mensual(
    hotel_id: int,
    anio: int,
    mes: int,
    conn=None,
) -> dict | None:
    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    score_promedio,
                    cambio_pct_vs_anterior,
                    total_reviews,
                    total_alertas
                FROM metricas_globales_mensual
                WHERE hotel_id = %s
                  AND anio = %s
                  AND mes = %s
                """,
                (hotel_id, anio, mes),
            )
            row = cur.fetchone()
            if row is None:
                return None

            cambio = row["cambio_pct_vs_anterior"]
            return {
                "score_promedio": float(row["score_promedio"]),
                "cambio_pct_vs_anterior": float(cambio) if cambio is not None else None,
                "total_reviews": int(row["total_reviews"]),
                "total_alertas": int(row["total_alertas"]),
            }

    return _exec(conn, _run)


def listar_topicos_mensual(
    hotel_id: int,
    anio: int,
    mes: int,
    *,
    tipo: str | None = None,
    solo_alertas: bool = False,
    conn=None,
) -> list[dict]:
    conditions = [
        "m.hotel_id = %s",
        "m.anio = %s",
        "m.mes = %s",
        "m.total_menciones > 0",
    ]
    params: list = [hotel_id, anio, mes]

    if tipo is not None:
        conditions.append("t.tipo = %s")
        params.append(tipo)
    if solo_alertas:
        conditions.append("m.alerta = TRUE")

    where_sql = " AND ".join(conditions)

    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT
                    m.topico_id,
                    t.slug,
                    t.nombre,
                    t.tipo,
                    m.score_promedio,
                    m.cambio_pct_vs_anterior,
                    m.total_menciones,
                    m.alerta
                FROM metricas_topico_mensual m
                JOIN topicos t ON t.id = m.topico_id
                WHERE {where_sql}
                ORDER BY t.id
                """,
                tuple(params),
            )
            rows = cur.fetchall()
        out = []
        for row in rows:
            cambio = row["cambio_pct_vs_anterior"]
            out.append({
                "topico_id": row["topico_id"],
                "slug": row["slug"],
                "nombre": row["nombre"],
                "tipo": row["tipo"],
                "score_promedio": float(row["score_promedio"]),
                "cambio_pct_vs_anterior": float(cambio) if cambio is not None else None,
                "total_menciones": int(row["total_menciones"]),
                "alerta": bool(row["alerta"]),
            })
        return out

    return _exec(conn, _run)


def listar_topicos_top5_mensual(
    hotel_id: int,
    anio: int,
    mes: int,
    conn=None,
) -> list[dict]:
    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    t.slug,
                    t.nombre,
                    m.score_promedio,
                    m.alerta
                FROM metricas_topico_mensual m
                JOIN topicos t ON t.id = m.topico_id
                WHERE m.hotel_id = %s
                  AND m.anio = %s
                  AND m.mes = %s
                  AND m.total_menciones > 0
                  AND m.alerta = TRUE
                ORDER BY m.score_promedio ASC, t.id ASC
                LIMIT 5
                """,
                (hotel_id, anio, mes),
            )
            rows = cur.fetchall()
        return [
            {
                "slug": row["slug"],
                "nombre": row["nombre"],
                "score_promedio": float(row["score_promedio"]),
                "alerta": bool(row["alerta"]),
            }
            for row in rows
        ]

    return _exec(conn, _run)


def obtener_topico_detalle_mensual(
    hotel_id: int,
    slug: str,
    anio: int,
    mes: int,
    conn=None,
) -> dict | None:
    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    t.id AS topico_id,
                    t.slug,
                    t.nombre,
                    t.umbral_alerta,
                    m.score_promedio,
                    m.cambio_pct_vs_anterior,
                    m.alerta,
                    m.total_menciones,
                    m.menciones_positivas,
                    m.menciones_negativas,
                    m.menciones_neutras
                FROM topicos t
                LEFT JOIN metricas_topico_mensual m
                       ON m.topico_id = t.id
                      AND m.hotel_id = %s
                      AND m.anio = %s
                      AND m.mes = %s
                WHERE t.slug = %s
                """,
                (hotel_id, anio, mes, slug),
            )
            row = cur.fetchone()

        if row is None:
            return None

        cambio = row["cambio_pct_vs_anterior"]
        return {
            "topico_id": int(row["topico_id"]),
            "slug": row["slug"],
            "nombre": row["nombre"],
            "umbral_alerta": int(row["umbral_alerta"]) if row["umbral_alerta"] is not None else None,
            "score_promedio": float(row["score_promedio"]) if row["score_promedio"] is not None else 0.0,
            "cambio_pct_vs_anterior": float(cambio) if cambio is not None else None,
            "alerta": bool(row["alerta"]) if row["alerta"] is not None else False,
            "total_menciones": int(row["total_menciones"]) if row["total_menciones"] is not None else 0,
            "menciones_positivas": int(row["menciones_positivas"]) if row["menciones_positivas"] is not None else 0,
            "menciones_negativas": int(row["menciones_negativas"]) if row["menciones_negativas"] is not None else 0,
            "menciones_neutras": int(row["menciones_neutras"]) if row["menciones_neutras"] is not None else 0,
        }

    return _exec(conn, _run)


def listar_fragmentos_topico_destacados(
    hotel_id: int,
    slug: str,
    anio: int,
    mes: int,
    *,
    limit: int = 3,
    conn=None,
) -> list[dict]:
    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    rt.sentimiento,
                    rt.fragmento,
                    rt.score_topico AS confianza
                FROM review_topicos rt
                JOIN reviews r ON r.id = rt.review_id
                JOIN topicos t ON t.id = rt.topico_id
                WHERE r.hotel_id = %s
                  AND t.slug = %s
                  AND EXTRACT(YEAR  FROM r.fecha_review) = %s
                  AND EXTRACT(MONTH FROM r.fecha_review) = %s
                  AND rt.fragmento IS NOT NULL
                  AND btrim(rt.fragmento) <> ''
                ORDER BY
                    CASE rt.sentimiento
                        WHEN 'negativo' THEN 0
                        WHEN 'neutro' THEN 1
                        ELSE 2
                    END ASC,
                    rt.score_topico DESC NULLS LAST,
                    rt.id DESC
                LIMIT %s
                """,
                (hotel_id, slug, anio, mes, limit),
            )
            rows = cur.fetchall()

        return [
            {
                "sentimiento": row["sentimiento"],
                "fragmento": row["fragmento"],
                "confianza": float(row["confianza"]) if row["confianza"] is not None else None,
            }
            for row in rows
        ]

    return _exec(conn, _run)


def listar_alertas(
    hotel_id: int,
    *,
    resuelta: bool = False,
    conn=None,
) -> list[dict]:
    def _run(c):
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    a.id AS alerta_id,
                    t.slug AS topico_slug,
                    t.nombre AS topico_nombre,
                    a.anio,
                    a.mes,
                    a.score_actual,
                    a.umbral_usado,
                    a.mensaje,
                    a.generada_en
                FROM alertas a
                JOIN topicos t ON t.id = a.topico_id
                WHERE a.hotel_id = %s
                  AND a.resuelta = %s
                ORDER BY a.generada_en DESC, a.id DESC
                """,
                (hotel_id, resuelta),
            )
            rows = cur.fetchall()

        out = []
        for row in rows:
            out.append({
                "alerta_id": int(row["alerta_id"]),
                "topico_slug": row["topico_slug"],
                "topico_nombre": row["topico_nombre"],
                "anio": int(row["anio"]),
                "mes": int(row["mes"]),
                "score_actual": float(row["score_actual"]) if row["score_actual"] is not None else None,
                "umbral_usado": int(row["umbral_usado"]) if row["umbral_usado"] is not None else None,
                "mensaje": row["mensaje"],
                "generada_en": row["generada_en"],
            })
        return out

    return _exec(conn, _run)
