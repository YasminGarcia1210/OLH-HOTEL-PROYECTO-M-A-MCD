"""
Tests unitarios — Fase 0: reglas de negocio puras (metricas_reglas.py).

Cubren:
- extraer_periodos: resolución de (anio, mes) a partir de fechas de reviews.
- calcular_score_global / calcular_score_topico: suavizado bayesiano (prior m, C).
- calcular_cambio_pct: variación respecto al mes anterior.
- es_alerta: comparación score vs umbral (topicos.umbral_alerta).
- tendencia_desde_cambio_pct: up / down / stable para respuestas de lectura.
"""

from datetime import date
from decimal import Decimal

import pytest

from services.metricas_reglas import (
    _score_bayesiano,
    calcular_cambio_pct,
    calcular_score_global,
    calcular_score_topico,
    es_alerta,
    extraer_periodos,
    tendencia_desde_cambio_pct,
)

# Prior por defecto alineado con Config (LAPLACE_PRIOR_M=0.6, LAPLACE_PRIOR_C=5)
M = Decimal("0.6")
C = Decimal("5")


# ── extraer_periodos ──────────────────────────────────────────────────────────

class TestExtraerPeriodos:
    def test_lista_vacia(self):
        assert extraer_periodos([]) == []

    def test_un_solo_mes(self):
        fechas = [date(2025, 11, 1), date(2025, 11, 15), date(2025, 11, 30)]
        assert extraer_periodos(fechas) == [(2025, 11)]

    def test_dos_meses_ordenados(self):
        fechas = [date(2025, 11, 3), date(2025, 10, 5), date(2025, 10, 20)]
        assert extraer_periodos(fechas) == [(2025, 10), (2025, 11)]

    def test_tres_meses_distintos(self):
        fechas = [
            date(2025, 12, 1),
            date(2025, 10, 1),
            date(2025, 11, 1),
        ]
        assert extraer_periodos(fechas) == [(2025, 10), (2025, 11), (2025, 12)]

    def test_cruza_anio(self):
        fechas = [date(2025, 12, 31), date(2026, 1, 1)]
        assert extraer_periodos(fechas) == [(2025, 12), (2026, 1)]

    def test_duplicados_consolidados(self):
        fechas = [date(2025, 11, 1)] * 50 + [date(2025, 11, 30)] * 50
        assert extraer_periodos(fechas) == [(2025, 11)]

    def test_una_sola_fecha(self):
        assert extraer_periodos([date(2025, 6, 15)]) == [(2025, 6)]


# ── calcular_score_global (m=0.6, C=5) ─────────────────────────────────────

class TestCalcularScoreGlobal:
    def test_caso_tipico(self):
        # (980 + 3) / (1432 + 5) * 100
        resultado = calcular_score_global(980, 1432, prior_m=M, prior_c=C)
        assert resultado == Decimal("68.41")

    def test_todos_positivos(self):
        assert calcular_score_global(100, 100, prior_m=M, prior_c=C) == Decimal("98.10")

    def test_ninguno_positivo(self):
        assert calcular_score_global(0, 500, prior_m=M, prior_c=C) == Decimal("0.59")

    def test_total_cero_devuelve_cero(self):
        """Sin reviews en el mes → 0.00 (NOT NULL en BD)."""
        assert calcular_score_global(0, 0, prior_m=M, prior_c=C) == Decimal("0.00")

    def test_redondeo_dos_decimales(self):
        resultado = calcular_score_global(1, 3, prior_m=M, prior_c=C)
        assert resultado == Decimal("50.00")

    def test_retorna_decimal(self):
        resultado = calcular_score_global(50, 100, prior_m=M, prior_c=C)
        assert isinstance(resultado, Decimal)


# ── calcular_score_topico (m=0.6, C=5) ────────────────────────────────────────

class TestCalcularScoreTopico:
    def test_caso_tipico(self):
        resultado = calcular_score_topico(200, 310, prior_m=M, prior_c=C)
        assert resultado == Decimal("64.44")

    def test_todos_positivos(self):
        assert calcular_score_topico(50, 50, prior_m=M, prior_c=C) == Decimal("96.36")

    def test_ninguno_positivo(self):
        assert calcular_score_topico(0, 100, prior_m=M, prior_c=C) == Decimal("2.86")

    def test_total_menciones_cero_devuelve_cero(self):
        assert calcular_score_topico(0, 0, prior_m=M, prior_c=C) == Decimal("0.00")

    def test_redondeo_dos_decimales(self):
        resultado = calcular_score_topico(2, 3, prior_m=M, prior_c=C)
        assert resultado == Decimal("62.50")

    def test_retorna_decimal(self):
        resultado = calcular_score_topico(10, 20, prior_m=M, prior_c=C)
        assert isinstance(resultado, Decimal)


# ── _score_bayesiano / casos destacados ───────────────────────────────────────

class TestScoreBayesiano:
    def test_una_review_positiva(self):
        """1 positiva / 1 total, m=0.6, C=5 → (1+3)/(1+5)*100."""
        r = _score_bayesiano(1, 1, prior_m=M, prior_c=C)
        assert r == Decimal("66.67")

    def test_una_review_negativa(self):
        """0 positivas / 1 total → (0+3)/(1+5)*100."""
        r = _score_bayesiano(0, 1, prior_m=M, prior_c=C)
        assert r == Decimal("50.00")

    def test_total_cero(self):
        assert _score_bayesiano(0, 0, prior_m=M, prior_c=C) == Decimal("0.00")

    def test_prior_degenerado_cero_recupera_proporcion_bruta(self):
        """C=0 → positivas/total × 100."""
        assert _score_bayesiano(1, 3, prior_m=Decimal("0.6"), prior_c=Decimal("0")) == Decimal("33.33")
        assert _score_bayesiano(980, 1432, prior_m=Decimal("0.6"), prior_c=Decimal("0")) == Decimal("68.44")


# ── calcular_cambio_pct ───────────────────────────────────────────────────────

class TestCalcularCambioPct:
    def test_sin_mes_anterior_devuelve_none(self):
        assert calcular_cambio_pct(Decimal("68.40"), None) is None

    def test_cambio_positivo(self):
        resultado = calcular_cambio_pct(Decimal("68.40"), Decimal("65.80"))
        assert resultado == Decimal("2.60")

    def test_cambio_negativo(self):
        resultado = calcular_cambio_pct(Decimal("60.00"), Decimal("65.00"))
        assert resultado == Decimal("-5.00")

    def test_sin_cambio(self):
        resultado = calcular_cambio_pct(Decimal("70.00"), Decimal("70.00"))
        assert resultado == Decimal("0.00")


# ── es_alerta ─────────────────────────────────────────────────────────────────

class TestEsAlerta:
    def test_bajo_umbral_genera_alerta(self):
        assert es_alerta(Decimal("52.30"), 65) is True

    def test_igual_umbral_no_genera_alerta(self):
        """Condición estricta: score < umbral (no ≤)."""
        assert es_alerta(Decimal("65.00"), 65) is False

    def test_sobre_umbral_no_genera_alerta(self):
        assert es_alerta(Decimal("80.00"), 65) is False

    def test_score_cero_genera_alerta(self):
        assert es_alerta(Decimal("0.00"), 65) is True

    def test_umbral_defecto_ddl(self):
        """El umbral por defecto en DDL es 65; validar comportamiento en el límite."""
        assert es_alerta(Decimal("64.99"), 65) is True
        assert es_alerta(Decimal("65.00"), 65) is False


# ── tendencia_desde_cambio_pct ────────────────────────────────────────────────

class TestTendenciaDesdeCambioPct:
    def test_none_es_stable(self):
        assert tendencia_desde_cambio_pct(None) == "stable"

    def test_positivo_up(self):
        assert tendencia_desde_cambio_pct(Decimal("1.3")) == "up"
        assert tendencia_desde_cambio_pct(1.3) == "up"

    def test_negativo_down(self):
        assert tendencia_desde_cambio_pct(Decimal("-5.2")) == "down"

    def test_cero_stable(self):
        assert tendencia_desde_cambio_pct(Decimal("0.00")) == "stable"
