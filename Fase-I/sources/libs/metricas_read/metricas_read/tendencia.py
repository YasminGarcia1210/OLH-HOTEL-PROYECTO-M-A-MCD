"""Derivación de tendencia para payloads de métricas (enum: up, down, stable)."""

from __future__ import annotations

from decimal import Decimal


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
