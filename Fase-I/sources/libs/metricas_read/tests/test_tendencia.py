from decimal import Decimal

from metricas_read.tendencia import tendencia_desde_cambio_pct


def test_stable_none():
    assert tendencia_desde_cambio_pct(None) == "stable"


def test_up_positive():
    assert tendencia_desde_cambio_pct(Decimal("1.5")) == "up"
    assert tendencia_desde_cambio_pct(2.0) == "up"


def test_down_negative():
    assert tendencia_desde_cambio_pct(Decimal("-0.1")) == "down"


def test_stable_zero():
    assert tendencia_desde_cambio_pct(Decimal("0")) == "stable"
