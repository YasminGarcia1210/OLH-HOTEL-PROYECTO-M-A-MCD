"""
Servicio para Reviews Explorer.

Responsabilidades:
  - Aplicar defaults de rango de fechas (últimos 30 días si no se especifica ninguna).
  - Orquestar count + list + tópicos desde el repositorio.
  - Armar el payload final alineado con ReviewsListResponse del contrato.
"""

import datetime
import logging
import math

from repositories import dashboard_reviews_repository as repo

logger = logging.getLogger(__name__)

_DEFAULT_RANGE_DAYS = 30


def get_reviews(conn, *, hotel_id: int, fecha_desde, fecha_hasta,
                sentimiento, topico_slug, topico_id,
                page: int, page_size: int, orden: str) -> dict:
    """
    Devuelve {'items': [...], 'paginacion': {...}} listo para serializar.

    Si fecha_desde y fecha_hasta son ambas None se aplica el rango por defecto
    de los últimos 30 días (hasta = hoy UTC).
    """
    if fecha_desde is None and fecha_hasta is None:
        hoy = datetime.date.today()
        fecha_hasta = hoy
        fecha_desde = hoy - datetime.timedelta(days=_DEFAULT_RANGE_DAYS)
        logger.info(
            "Sin rango de fechas explícito; aplicando default: %s – %s",
            fecha_desde, fecha_hasta,
        )

    filters = {
        "hotel_id":    hotel_id,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "sentimiento": sentimiento,
        "topico_slug": topico_slug,
        "topico_id":   topico_id,
    }

    total = repo.count_reviews_filtradas(conn, filters)
    filas = repo.list_reviews_paginadas(conn, filters, page, page_size, orden)

    review_ids = [f["review_id"] for f in filas]
    topicos_por_review = repo.list_topicos_por_reviews(conn, review_ids)

    items = [_map_item(fila, topicos_por_review) for fila in filas]

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return {
        "items": items,
        "paginacion": {
            "page":        page,
            "page_size":   page_size,
            "total":       total,
            "total_pages": total_pages,
        },
    }


def _map_item(fila: dict, topicos_por_review: dict) -> dict:
    fecha = fila["fecha_review"]
    fecha_str = fecha.isoformat() if isinstance(fecha, datetime.date) else str(fecha)

    return {
        "review_id":    fila["review_id"],
        "hotel_id":     fila["hotel_id"],
        "fecha_review": fecha_str,
        "texto_limpio": fila["texto_limpio"],
        "plataforma":   fila.get("plataforma"),
        "idioma":       fila.get("idioma"),
        "titulo":       None,
        "prediccion": {
            "sentimiento":    fila["sentimiento"],
            "confianza":      float(fila["confianza"]) if fila["confianza"] is not None else None,
            "modelo_version": fila["modelo_version"],
        },
        "topicos": topicos_por_review.get(fila["review_id"], []),
    }
