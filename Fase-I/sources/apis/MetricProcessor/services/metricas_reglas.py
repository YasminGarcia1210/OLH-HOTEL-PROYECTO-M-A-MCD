"""
Reglas de negocio puras para el cálculo de métricas mensuales.

Todas las funciones de este módulo son puras (sin efectos secundarios ni acceso
a BD) y pueden usarse directamente en tests unitarios.

Score global y por tópico (suavizado bayesiano / prior del corpus):

  score = ((positivas + C · m) / (total + C)) × 100

  - `positivas`: reviews_positivas (global) o menciones_positivas (tópico).
  - `total`: total_reviews o total_menciones.
  - `m` ∈ [0, 1]: prior de proporción positiva (ej. media del corpus).
  - `C` ≥ 0: peso equivalente del prior (C = 0 recupera la proporción bruta).

Los valores `m` y `C` los inyecta el orquestador (`metricas_service`) desde
`Config` (env `LAPLACE_PRIOR_M`, `LAPLACE_PRIOR_C`).

Si total == 0 → Decimal("0.00") (evita inflar meses vacíos en series).

Resolución de período:
  Un archivo puede contener reviews de varios meses naturales.
  El job NO bloquea archivos multi-mes: para cada (anio, mes) distinto detectado
  en reviews.fecha_review se calcula y persiste un registro independiente (UPSERT).
  La respuesta de POST /calcular incluye todos los períodos tocados (opción C).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP


# ── Período ───────────────────────────────────────────────────────────────────

def extraer_periodos(fechas: list[date]) -> list[tuple[int, int]]:
    """
    Dado un listado de fechas de reviews, devuelve los meses naturales distintos
    ordenados cronológicamente como tuplas (anio, mes).

    Reglas:
    - Fechas duplicadas dentro del mismo mes se consolidan en una sola tupla.
    - La lista resultante está ordenada de más antiguo a más reciente.
    - Si `fechas` está vacía, devuelve una lista vacía (sin error; el servicio
      levantará SinReviewsError antes de llegar aquí si es necesario).

    Ejemplos:
        >>> extraer_periodos([date(2025, 11, 1), date(2025, 11, 30)])
        [(2025, 11)]
        >>> extraer_periodos([date(2025, 10, 5), date(2025, 11, 3), date(2025, 10, 20)])
        [(2025, 10), (2025, 11)]
    """
    if not fechas:
        return []
    periodos = sorted({(f.year, f.month) for f in fechas})
    return periodos


# ── Scores ────────────────────────────────────────────────────────────────────

def _score_bayesiano(
    positivas: int,
    total: int,
    *,
    prior_m: Decimal,
    prior_c: Decimal,
) -> Decimal:
    """
    Proporción positiva suavizada × 100, redondeada a 2 decimales (ROUND_HALF_UP).

    Si total == 0 devuelve 0.00 (NOT NULL en tablas de métricas).
    """
    if total == 0:
        return Decimal("0.00")
    num = Decimal(positivas) + prior_c * prior_m
    den = Decimal(total) + prior_c
    score = num / den * Decimal("100")
    return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_score_global(
    reviews_positivas: int,
    total_reviews: int,
    *,
    prior_m: Decimal,
    prior_c: Decimal,
) -> Decimal:
    """
    Score global mensual con suavizado bayesiano.

    Ver `_score_bayesiano` para la fórmula. Alineado con NUMERIC(5,2) del DDL.
    """
    return _score_bayesiano(
        reviews_positivas, total_reviews, prior_m=prior_m, prior_c=prior_c
    )


def calcular_score_topico(
    menciones_positivas: int,
    total_menciones: int,
    *,
    prior_m: Decimal,
    prior_c: Decimal,
) -> Decimal:
    """
    Score por tópico con suavizado bayesiano.

    Ver `_score_bayesiano`. Alineado con NUMERIC(5,2) del DDL.
    """
    return _score_bayesiano(
        menciones_positivas, total_menciones, prior_m=prior_m, prior_c=prior_c
    )


def calcular_cambio_pct(score_actual: Decimal, score_anterior: Decimal | None) -> Decimal | None:
    """
    Variación porcentual puntual respecto al mes anterior.

    Devuelve None cuando no existe registro previo (primer mes del hotel).
    El resultado se redondea a 2 decimales (ROUND_HALF_UP), alineado con
    NUMERIC(6,2) del DDL (permite hasta ±999.99).
    """
    if score_anterior is None:
        return None
    cambio = score_actual - score_anterior
    return cambio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── Alertas ───────────────────────────────────────────────────────────────────

def es_alerta(score_promedio: Decimal, umbral_alerta: int) -> bool:
    """
    Determina si un tópico debe generar alerta.

    Condición: score_promedio < umbral_alerta (fuente: topicos.umbral_alerta).
    El umbral es un valor entero (SMALLINT en el DDL); el score es NUMERIC(5,2).
    """
    return score_promedio < Decimal(umbral_alerta)


# ── Presentación (lecturas dashboard / contrato OpenAPI) ─────────────────────

def tendencia_desde_cambio_pct(cambio_pct_vs_anterior: Decimal | float | None) -> str:
    """
    Deriva `tendencia` para payloads de métricas por tópico (enum: up, down, stable).

    Sin mes anterior persistido (`cambio_pct_vs_anterior` es None) se considera estable.
    """
    if cambio_pct_vs_anterior is None:
        return "stable"
    c = (
        cambio_pct_vs_anterior
        if isinstance(cambio_pct_vs_anterior, Decimal)
        else Decimal(str(cambio_pct_vs_anterior))
    )
    if c > 0:
        return "up"
    if c < 0:
        return "down"
    return "stable"
