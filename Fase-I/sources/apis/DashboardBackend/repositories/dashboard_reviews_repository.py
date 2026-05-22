"""
Repositorio para Reviews Explorer.

Tablas: reviews, predicciones_sentimiento, review_topicos, topicos.
Todas las funciones aceptan una conexión abierta del pool (psycopg2) y usan
RealDictCursor para devolver filas como dicts.
"""

import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def _build_where(filters: dict) -> tuple[str, list]:
    """
    Construye la cláusula WHERE compartida entre count y list.

    filters:
      hotel_id        int   (obligatorio)
      fecha_desde     date  (opcional)
      fecha_hasta     date  (opcional)
      sentimiento     str   (opcional)
      topico_slug     str   (opcional, prevalece sobre topico_id)
      topico_id       int   (opcional)
    """
    clauses = ["r.hotel_id = %s"]
    params: list = [filters["hotel_id"]]

    if filters.get("fecha_desde"):
        clauses.append("r.fecha_review >= %s")
        params.append(filters["fecha_desde"])

    if filters.get("fecha_hasta"):
        clauses.append("r.fecha_review <= %s")
        params.append(filters["fecha_hasta"])

    if filters.get("sentimiento"):
        clauses.append("ps.sentimiento = %s")
        params.append(filters["sentimiento"])

    if filters.get("topico_slug"):
        clauses.append(
            "EXISTS ("
            "  SELECT 1 FROM review_topicos rt"
            "  JOIN topicos t ON t.id = rt.topico_id"
            "  WHERE rt.review_id = r.id AND t.slug = %s"
            ")"
        )
        params.append(filters["topico_slug"])
    elif filters.get("topico_id"):
        clauses.append(
            "EXISTS ("
            "  SELECT 1 FROM review_topicos rt"
            "  WHERE rt.review_id = r.id AND rt.topico_id = %s"
            ")"
        )
        params.append(filters["topico_id"])

    return " AND ".join(clauses), params


def count_reviews_filtradas(conn, filters: dict) -> int:
    """Devuelve el total de reviews que cumplen los filtros (sin paginar)."""
    where, params = _build_where(filters)
    sql = f"""
        SELECT COUNT(*) AS total
        FROM reviews r
        INNER JOIN predicciones_sentimiento ps ON ps.review_id = r.id
        WHERE {where}
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row["total"] if row else 0


def list_reviews_paginadas(conn, filters: dict, page: int, page_size: int, orden: str) -> list[dict]:
    """
    Devuelve las filas de reviews (con predicción) para la página solicitada.
    Los tópicos se buscan en una segunda consulta por list_topicos_por_reviews.
    """
    where, params = _build_where(filters)
    order_dir = "DESC" if orden == "fecha_desc" else "ASC"
    offset = (page - 1) * page_size

    sql = f"""
        SELECT
            r.id            AS review_id,
            r.hotel_id,
            r.fecha_review,
            r.texto_limpio,
            r.plataforma,
            r.idioma,
            ps.sentimiento,
            ps.confianza,
            ps.modelo_version
        FROM reviews r
        INNER JOIN predicciones_sentimiento ps ON ps.review_id = r.id
        WHERE {where}
        ORDER BY r.fecha_review {order_dir}
        LIMIT %s OFFSET %s
    """
    params_pag = params + [page_size, offset]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params_pag)
        return [dict(row) for row in cur.fetchall()]


def list_topicos_por_reviews(conn, review_ids: list[int]) -> dict[int, list[dict]]:
    """
    Dado un listado de review_id, devuelve un dict {review_id: [topico_dict, ...]}.
    Usado para hidratar el array `topicos` de cada ReviewListItem.
    """
    if not review_ids:
        return {}

    placeholders = ",".join(["%s"] * len(review_ids))
    sql = f"""
        SELECT
            rt.review_id,
            t.id        AS topico_id,
            t.slug,
            t.nombre,
            rt.score_topico,
            rt.sentimiento,
            rt.fragmento
        FROM review_topicos rt
        JOIN topicos t ON t.id = rt.topico_id
        WHERE rt.review_id IN ({placeholders})
        ORDER BY rt.review_id, t.id
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, review_ids)
        rows = cur.fetchall()

    result: dict[int, list[dict]] = {}
    for row in rows:
        rid = row["review_id"]
        result.setdefault(rid, []).append({
            "topico_id":   row["topico_id"],
            "slug":        row["slug"],
            "nombre":      row["nombre"],
            "score_topico": float(row["score_topico"]) if row["score_topico"] is not None else None,
            "sentimiento": row["sentimiento"],
            "fragmento":   row["fragmento"],
        })
    return result
