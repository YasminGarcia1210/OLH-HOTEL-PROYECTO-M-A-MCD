"""Servicio de consulta de métricas (solo lectura)."""

from __future__ import annotations

import logging
from datetime import date, timezone

from metricas_read import repository as metricas_repo
from metricas_read.exceptions import TopicoNoEncontradoError
from metricas_read.tendencia import tendencia_desde_cambio_pct

logger = logging.getLogger(__name__)


def obtener_kpis_mensual(hotel_id: int, anio: int, mes: int) -> dict:
    logger.info("KPIs mensuales hotel_id=%s periodo=%s-%02d", hotel_id, anio, mes)
    fila = metricas_repo.obtener_kpis_mensual(hotel_id, anio, mes)

    if fila is None:
        return {
            "sentimiento_promedio": {
                "score": 0.0,
                "cambio_pct": 0.0,
                "tendencia": "stable",
            },
            "reviews_analizadas": 0,
            "topicos_con_alerta": 0,
        }

    cambio_pct = fila["cambio_pct_vs_anterior"]
    return {
        "sentimiento_promedio": {
            "score": fila["score_promedio"],
            "cambio_pct": cambio_pct if cambio_pct is not None else 0.0,
            "tendencia": tendencia_desde_cambio_pct(cambio_pct),
        },
        "reviews_analizadas": fila["total_reviews"],
        "topicos_con_alerta": fila["total_alertas"],
    }


def _rango_desde_meses(meses: int) -> tuple[int, int, int, int]:
    hoy = date.today()
    hasta_anio, hasta_mes = hoy.year, hoy.month
    total = hasta_anio * 12 + hasta_mes
    inicio = total - (meses - 1)
    desde_anio = (inicio - 1) // 12
    desde_mes = (inicio - 1) % 12 + 1
    return desde_anio, desde_mes, hasta_anio, hasta_mes


def obtener_sentimiento_mensual(
    hotel_id: int,
    meses: int | None = None,
    desde: str | None = None,
    hasta: str | None = None,
) -> list[dict]:
    if desde is not None and hasta is not None:
        desde_anio, desde_mes = int(desde[:4]), int(desde[5:])
        hasta_anio, hasta_mes = int(hasta[:4]), int(hasta[5:])
    else:
        n = meses if meses is not None else 12
        desde_anio, desde_mes, hasta_anio, hasta_mes = _rango_desde_meses(n)

    logger.info(
        "Serie mensual hotel_id=%s rango=%s-%02d → %s-%02d",
        hotel_id, desde_anio, desde_mes, hasta_anio, hasta_mes,
    )
    return metricas_repo.listar_sentimiento_mensual(
        hotel_id, desde_anio, desde_mes, hasta_anio, hasta_mes
    )


def obtener_topicos_mensual(
    hotel_id: int,
    anio: int,
    mes: int,
    *,
    tipo: str | None = None,
    solo_alertas: bool = False,
) -> list[dict]:
    logger.info(
        "Listado tópicos mensuales hotel_id=%s %s-%02d tipo=%s solo_alertas=%s",
        hotel_id, anio, mes, tipo, solo_alertas,
    )
    filas = metricas_repo.listar_topicos_mensual(
        hotel_id, anio, mes, tipo=tipo, solo_alertas=solo_alertas
    )
    return [
        {
            **row,
            "tendencia": tendencia_desde_cambio_pct(row["cambio_pct_vs_anterior"]),
        }
        for row in filas
    ]


def obtener_topicos_top5_mensual(
    hotel_id: int,
    anio: int,
    mes: int,
) -> list[dict]:
    logger.info(
        "Top 5 tópicos críticos hotel_id=%s %s-%02d",
        hotel_id, anio, mes,
    )
    filas = metricas_repo.listar_topicos_top5_mensual(hotel_id, anio, mes)
    return [
        {
            "posicion": idx,
            **row,
        }
        for idx, row in enumerate(filas, start=1)
    ]


def obtener_topico_detalle_mensual(
    hotel_id: int,
    slug: str,
    anio: int,
    mes: int,
) -> dict:
    logger.info(
        "Detalle tópico hotel_id=%s slug=%s periodo=%s-%02d",
        hotel_id, slug, anio, mes,
    )
    detalle = metricas_repo.obtener_topico_detalle_mensual(hotel_id, slug, anio, mes)
    if detalle is None:
        raise TopicoNoEncontradoError(f"El tópico '{slug}' no existe")

    fragmentos = metricas_repo.listar_fragmentos_topico_destacados(
        hotel_id, slug, anio, mes, limit=3
    )

    return {
        "slug": detalle["slug"],
        "nombre": detalle["nombre"],
        "score_promedio": detalle["score_promedio"],
        "cambio_pct_vs_anterior": detalle["cambio_pct_vs_anterior"],
        "alerta": detalle["alerta"],
        "umbral_alerta": detalle["umbral_alerta"],
        "menciones": {
            "total": detalle["total_menciones"],
            "positivas": detalle["menciones_positivas"],
            "negativas": detalle["menciones_negativas"],
            "neutras": detalle["menciones_neutras"],
        },
        "fragmentos_destacados": fragmentos,
    }


def _iso_z(dt) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def obtener_alertas(
    hotel_id: int,
    *,
    resuelta: bool = False,
) -> list[dict]:
    logger.info("Listado alertas hotel_id=%s resuelta=%s", hotel_id, resuelta)
    filas = metricas_repo.listar_alertas(hotel_id, resuelta=resuelta)
    return [
        {
            **row,
            "generada_en": _iso_z(row["generada_en"]),
        }
        for row in filas
    ]
