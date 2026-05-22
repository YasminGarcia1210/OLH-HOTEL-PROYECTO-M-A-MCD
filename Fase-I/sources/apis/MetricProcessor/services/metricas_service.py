"""
Servicio de cálculo de métricas (pipeline batch).

Orquesta POST /api/v1/metricas/calcular y POST /api/v1/metricas/recalcular.
Las lecturas para el dashboard están en el paquete `metricas_read` y se exponen
vía DashboardBackend.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import db
from config import Config
from repositories import archivo_repository as archivo_repo
from repositories import metricas_repository as metricas_repo
from services.exceptions import (
    ArchivoNoEncontradoError,
    EstadoInvalidoError,
    HotelNoAsignadoError,
    PeriodoNoEncontradoError,
    SinReviewsError,
)
from services.metricas_reglas import (
    calcular_cambio_pct,
    calcular_score_global,
    calcular_score_topico,
    es_alerta,
    extraer_periodos,
)

logger = logging.getLogger(__name__)

_PRIOR_M = Decimal(str(Config.LAPLACE_PRIOR_M))
_PRIOR_C = Decimal(str(Config.LAPLACE_PRIOR_C))


def calcular_metricas(archivo_id: int) -> dict:
    """
    Ejecuta el pipeline completo y devuelve el payload del contrato.
    Lanza excepciones de dominio ante condiciones inválidas; la ruta las traduce a HTTP.
    """
    archivo = archivo_repo.obtener_archivo(archivo_id)
    if archivo is None:
        raise ArchivoNoEncontradoError(f"archivo_id={archivo_id} no encontrado en log_archivos")

    if archivo["estado"] != "topics_identified":
        raise EstadoInvalidoError(
            f"archivo_id={archivo_id} tiene estado '{archivo['estado']}'; se requiere 'topics_identified'"
        )

    hotel_id = archivo["hotel_id"]
    if hotel_id is None:
        raise HotelNoAsignadoError(
            f"archivo_id={archivo_id} no tiene hotel_id asignado"
        )

    fechas = metricas_repo.obtener_fechas_reviews(archivo_id)
    if not fechas:
        raise SinReviewsError(f"archivo_id={archivo_id} no tiene reviews asociadas")

    periodos = extraer_periodos(fechas)
    logger.info(
        "archivo_id=%s hotel_id=%s — %s período(s): %s",
        archivo_id, hotel_id, len(periodos), periodos,
    )

    metricas_por_periodo = []

    with db.get_connection() as conn:
        for anio, mes in periodos:
            resultado_periodo = _calcular_periodo(
                conn, archivo_id, hotel_id, anio, mes
            )
            metricas_por_periodo.append(resultado_periodo)

        archivo_repo.marcar_completado(archivo_id, conn=conn)

    logger.info(
        "archivo_id=%s completed — %s período(s) procesados",
        archivo_id, len(periodos),
    )

    return {
        "archivo_id": archivo_id,
        "estado": "completed",
        "periodos": [{"anio": a, "mes": m} for a, m in periodos],
        "metricas_por_periodo": metricas_por_periodo,
        "fecha_metricas": datetime.now(timezone.utc).isoformat(),
    }


def recalcular_periodo(hotel_id: int, anio: int, mes: int) -> dict:
    """
    Recalcula scores y alertas para un (hotel_id, anio, mes) usando conteos ya
    persistidos en metricas_globales_mensual y metricas_topico_mensual.
    """
    logger.info("Recalcular métricas hotel_id=%s período=%s-%02d", hotel_id, anio, mes)

    with db.get_connection() as conn:
        fila_global = metricas_repo.obtener_metricas_global_persistida(
            hotel_id, anio, mes, conn=conn
        )
        if fila_global is None:
            raise PeriodoNoEncontradoError(
                f"No hay métricas globales para hotel_id={hotel_id} {anio}-{mes:02d}"
            )

        total_reviews = fila_global["total_reviews"]
        reviews_positivas = fila_global["reviews_positivas"]
        reviews_negativas = fila_global["reviews_negativas"]
        reviews_neutras = fila_global["reviews_neutras"]

        score_global = calcular_score_global(
            reviews_positivas,
            total_reviews,
            prior_m=_PRIOR_M,
            prior_c=_PRIOR_C,
        )
        score_global_anterior = metricas_repo.obtener_score_global_anterior(
            hotel_id, anio, mes, conn=conn
        )
        cambio_global = calcular_cambio_pct(score_global, score_global_anterior)

        topicos = metricas_repo.listar_metricas_topicos_persistidas(
            hotel_id, anio, mes, conn=conn
        )

        alertas_generadas = []
        metricas_repo.eliminar_alertas_no_resueltas(hotel_id, anio, mes, conn=conn)

        for topico in topicos:
            topico_id = topico["topico_id"]
            umbral = topico["umbral_alerta"]
            total_men = topico["total_menciones"]
            men_pos = topico["menciones_positivas"]
            men_neg = topico["menciones_negativas"]
            men_neu = topico["menciones_neutras"]

            score_top = calcular_score_topico(
                men_pos,
                total_men,
                prior_m=_PRIOR_M,
                prior_c=_PRIOR_C,
            )
            score_top_anterior = metricas_repo.obtener_score_topico_anterior(
                hotel_id, topico_id, anio, mes, conn=conn
            )
            cambio_top = calcular_cambio_pct(score_top, score_top_anterior)
            tiene_alerta = es_alerta(score_top, umbral) if umbral is not None else False

            metricas_repo.upsert_topico(
                hotel_id, topico_id, anio, mes,
                total_menciones=total_men,
                menciones_positivas=men_pos,
                menciones_negativas=men_neg,
                menciones_neutras=men_neu,
                score_promedio=score_top,
                cambio_pct_vs_anterior=cambio_top,
                alerta=tiene_alerta,
                conn=conn,
            )

            if tiene_alerta:
                metricas_repo.insertar_alerta(
                    hotel_id, topico_id, anio, mes,
                    score_actual=score_top,
                    umbral_usado=umbral,
                    conn=conn,
                )
                alertas_generadas.append({
                    "topico_slug": topico["slug"],
                    "score_actual": float(score_top),
                })

        total_alertas = len(alertas_generadas)
        metricas_repo.upsert_global(
            hotel_id, anio, mes,
            total_reviews=total_reviews,
            reviews_positivas=reviews_positivas,
            reviews_negativas=reviews_negativas,
            reviews_neutras=reviews_neutras,
            score_promedio=score_global,
            cambio_pct_vs_anterior=cambio_global,
            total_alertas=total_alertas,
            conn=conn,
        )

    return {
        "periodo": {"anio": anio, "mes": mes},
        "hotel_id": hotel_id,
        "global": {
            "score_promedio": float(score_global),
            "cambio_pct_vs_anterior": float(cambio_global) if cambio_global is not None else None,
            "total_reviews": total_reviews,
            "reviews_positivas": reviews_positivas,
            "reviews_negativas": reviews_negativas,
            "reviews_neutras": reviews_neutras,
        },
        "alertas_generadas": alertas_generadas,
        "fecha_metricas": datetime.now(timezone.utc).isoformat(),
    }


def _calcular_periodo(conn, archivo_id: int, hotel_id: int, anio: int, mes: int) -> dict:
    logger.info("Procesando período %s-%02d para archivo_id=%s", anio, mes, archivo_id)

    conteos = metricas_repo.contar_reviews_por_sentimiento(
        hotel_id, anio, mes, conn=conn
    )
    total_reviews = conteos["total"]
    reviews_positivas = conteos["positivas"]
    reviews_negativas = conteos["negativas"]
    reviews_neutras = conteos["neutras"]

    score_global = calcular_score_global(
        reviews_positivas,
        total_reviews,
        prior_m=_PRIOR_M,
        prior_c=_PRIOR_C,
    )
    score_global_anterior = metricas_repo.obtener_score_global_anterior(
        hotel_id, anio, mes, conn=conn
    )
    cambio_global = calcular_cambio_pct(score_global, score_global_anterior)

    topicos = metricas_repo.obtener_topicos_con_menciones(
        hotel_id, anio, mes, conn=conn
    )

    alertas_generadas = []
    metricas_repo.eliminar_alertas_no_resueltas(hotel_id, anio, mes, conn=conn)

    for topico in topicos:
        topico_id = topico["topico_id"]
        umbral = topico["umbral_alerta"]
        total_men = topico["total_menciones"]
        men_pos = topico["menciones_positivas"]
        men_neg = topico["menciones_negativas"]
        men_neu = topico["menciones_neutras"]

        score_top = calcular_score_topico(
            men_pos,
            total_men,
            prior_m=_PRIOR_M,
            prior_c=_PRIOR_C,
        )
        score_top_anterior = metricas_repo.obtener_score_topico_anterior(
            hotel_id, topico_id, anio, mes, conn=conn
        )
        cambio_top = calcular_cambio_pct(score_top, score_top_anterior)
        tiene_alerta = es_alerta(score_top, umbral) if umbral is not None else False

        metricas_repo.upsert_topico(
            hotel_id, topico_id, anio, mes,
            total_menciones=total_men,
            menciones_positivas=men_pos,
            menciones_negativas=men_neg,
            menciones_neutras=men_neu,
            score_promedio=score_top,
            cambio_pct_vs_anterior=cambio_top,
            alerta=tiene_alerta,
            conn=conn,
        )

        if tiene_alerta:
            metricas_repo.insertar_alerta(
                hotel_id, topico_id, anio, mes,
                score_actual=score_top,
                umbral_usado=umbral,
                conn=conn,
            )
            alertas_generadas.append({
                "topico_slug": topico["slug"],
                "score_actual": float(score_top),
            })

    total_alertas = len(alertas_generadas)
    metricas_repo.upsert_global(
        hotel_id, anio, mes,
        total_reviews=total_reviews,
        reviews_positivas=reviews_positivas,
        reviews_negativas=reviews_negativas,
        reviews_neutras=reviews_neutras,
        score_promedio=score_global,
        cambio_pct_vs_anterior=cambio_global,
        total_alertas=total_alertas,
        conn=conn,
    )

    return {
        "periodo": {"anio": anio, "mes": mes},
        "global": {
            "score_promedio": float(score_global),
            "cambio_pct_vs_anterior": float(cambio_global) if cambio_global is not None else None,
            "total_reviews": total_reviews,
            "reviews_positivas": reviews_positivas,
            "reviews_negativas": reviews_negativas,
            "reviews_neutras": reviews_neutras,
        },
        "alertas_generadas": alertas_generadas,
    }
