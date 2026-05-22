"""
Orquestación: recalcular los últimos 6 meses (incl. mes actual) vía MetricProcessor.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

import requests

from config import Config
from services.exceptions import MetricProcessorIndisponibleError

logger = logging.getLogger(__name__)

_MESES_SEMESTRE = 6


def _restar_meses(anio: int, mes: int, n: int) -> tuple[int, int]:
    """Resta n meses a (anio, mes); mes en 1..12."""
    total = anio * 12 + (mes - 1) - n
    nuevo_anio = total // 12
    nuevo_mes = total % 12 + 1
    return nuevo_anio, nuevo_mes


def _periodos_ultimos_seis_meses(fecha_ref: date) -> list[tuple[int, int]]:
    """
    Últimos 6 meses naturales incluyendo el mes de fecha_ref, orden cronológico ascendente.
    Ej. fecha_ref 2026-05-12 → [(2025, 12), (2026, 1), …, (2026, 5)].
    """
    anio, mes = fecha_ref.year, fecha_ref.month
    inicio_anio, inicio_mes = _restar_meses(anio, mes, _MESES_SEMESTRE - 1)
    out: list[tuple[int, int]] = []
    y, m = inicio_anio, inicio_mes
    for _ in range(_MESES_SEMESTRE):
        out.append((y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return out


def _parse_error_envelope(payload: Any) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None
    err = payload.get("error")
    if not isinstance(err, dict):
        return None, None
    codigo = err.get("codigo")
    mensaje = err.get("mensaje")
    c = str(codigo) if codigo is not None else None
    msg = str(mensaje) if mensaje is not None else None
    return c, msg


def recalcular_semestre(hotel_id: int, *, fecha_referencia: date | None = None) -> dict:
    """
    Recalcula 6 meses (incluyendo el mes de `fecha_referencia` o el actual UTC),
    llamando secuencialmente a MetricProcessor POST /api/v1/metricas/recalcular
    en orden cronológico ascendente. Devuelve un resumen.
    """
    if fecha_referencia is None:
        fecha_referencia = datetime.now(timezone.utc).date()

    periodos = _periodos_ultimos_seis_meses(fecha_referencia)
    url = f"{Config.METRIC_PROCESSOR_URL}/api/v1/metricas/recalcular"
    timeout = Config.METRIC_PROCESSOR_TIMEOUT_SECONDS

    t0 = datetime.now(timezone.utc)
    exitos = 0
    fallidos: list[dict[str, Any]] = []

    for anio, mes in periodos:
        try:
            resp = requests.post(
                url,
                json={"hotel_id": hotel_id, "anio": anio, "mes": mes},
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout llamando a MetricProcessor %s-%02d: %s", anio, mes, exc)
            raise MetricProcessorIndisponibleError(
                f"MetricProcessor no respondió a tiempo (timeout {timeout}s)."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Conexión fallida a MetricProcessor: %s", exc)
            raise MetricProcessorIndisponibleError(
                "No se pudo conectar con MetricProcessor."
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Error de red con MetricProcessor: %s", exc, exc_info=True)
            raise MetricProcessorIndisponibleError(
                f"Error al comunicarse con MetricProcessor: {exc}"
            ) from exc

        if resp.status_code == 200:
            exitos += 1
            continue

        try:
            payload = resp.json()
        except ValueError:
            payload = None
        codigo, mensaje = _parse_error_envelope(payload)
        fallidos.append({
            "anio": anio,
            "mes": mes,
            "http_status": resp.status_code,
            "codigo": codigo or "ERROR_DESCONOCIDO",
            "mensaje": mensaje or resp.text[:500] if resp.text else None,
        })

    t1 = datetime.now(timezone.utc)
    primer = periodos[0]
    ultimo = periodos[-1]

    return {
        "hotel_id": hotel_id,
        "primer_periodo": {"anio": primer[0], "mes": primer[1]},
        "ultimo_periodo": {"anio": ultimo[0], "mes": ultimo[1]},
        "periodos_solicitados": _MESES_SEMESTRE,
        "exitos": exitos,
        "fallos": len(fallidos),
        "fallidos": fallidos,
        "fecha_inicio": t0.isoformat(),
        "fecha_fin": t1.isoformat(),
    }
