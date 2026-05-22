"""
Tests de GET /api/v1/metricas/kpis.

Cubren:
- Validación de query params (validar_query_kpis_mensual).
- Lógica de servicio (obtener_kpis_mensual) y fallback sin datos.
- Mapeo HTTP: envelope, códigos de estado y delegación al servicio.
"""

from unittest.mock import patch

import pytest

from app import create_app
from metricas_read.service import obtener_kpis_mensual
from routes.validators import validar_query_kpis_mensual

ENDPOINT = "/api/v1/metricas/kpis"

KPIS_MOCK = {
    "sentimiento_promedio": {
        "score": 68.4,
        "cambio_pct": 2.1,
        "tendencia": "up",
    },
    "reviews_analizadas": 1432,
    "topicos_con_alerta": 2,
}


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestValidadorQueryKpis:
    def test_valido_minimo(self):
        assert validar_query_kpis_mensual(
            {"hotel_id": "1", "anio": "2025", "mes": "11"}
        ) == []

    def test_hotel_id_faltante(self):
        errores = validar_query_kpis_mensual({"anio": "2025", "mes": "11"})
        assert any("hotel_id" in e for e in errores)

    def test_hotel_id_invalido(self):
        errores = validar_query_kpis_mensual(
            {"hotel_id": "abc", "anio": "2025", "mes": "11"}
        )
        assert any("hotel_id" in e for e in errores)

    def test_anio_faltante(self):
        errores = validar_query_kpis_mensual({"hotel_id": "1", "mes": "11"})
        assert any("anio" in e for e in errores)

    def test_anio_menor_a_2020(self):
        errores = validar_query_kpis_mensual(
            {"hotel_id": "1", "anio": "2019", "mes": "11"}
        )
        assert any("anio" in e for e in errores)

    def test_mes_faltante(self):
        errores = validar_query_kpis_mensual({"hotel_id": "1", "anio": "2025"})
        assert any("mes" in e for e in errores)

    def test_mes_fuera_de_rango(self):
        errores = validar_query_kpis_mensual(
            {"hotel_id": "1", "anio": "2025", "mes": "13"}
        )
        assert any("mes" in e for e in errores)


class TestServicioKpisMensual:
    @patch("metricas_read.service.metricas_repo.obtener_kpis_mensual")
    def test_mapea_resultado_y_tendencia_up(self, mock_repo):
        mock_repo.return_value = {
            "score_promedio": 68.4,
            "cambio_pct_vs_anterior": 2.1,
            "total_reviews": 1432,
            "total_alertas": 2,
        }
        out = obtener_kpis_mensual(1, 2025, 11)
        assert out == KPIS_MOCK

    @patch("metricas_read.service.metricas_repo.obtener_kpis_mensual")
    def test_mapea_tendencia_down(self, mock_repo):
        mock_repo.return_value = {
            "score_promedio": 52.3,
            "cambio_pct_vs_anterior": -5.2,
            "total_reviews": 310,
            "total_alertas": 4,
        }
        out = obtener_kpis_mensual(2, 2025, 11)
        assert out["sentimiento_promedio"]["tendencia"] == "down"

    @patch("metricas_read.service.metricas_repo.obtener_kpis_mensual")
    def test_cambio_none_retorna_stable_y_cambio_cero(self, mock_repo):
        mock_repo.return_value = {
            "score_promedio": 70.0,
            "cambio_pct_vs_anterior": None,
            "total_reviews": 100,
            "total_alertas": 1,
        }
        out = obtener_kpis_mensual(3, 2025, 11)
        assert out["sentimiento_promedio"]["tendencia"] == "stable"
        assert out["sentimiento_promedio"]["cambio_pct"] == 0.0

    @patch("metricas_read.service.metricas_repo.obtener_kpis_mensual")
    def test_sin_datos_retorna_fallback_en_ceros(self, mock_repo):
        mock_repo.return_value = None
        out = obtener_kpis_mensual(10, 2025, 11)
        assert out == {
            "sentimiento_promedio": {
                "score": 0.0,
                "cambio_pct": 0.0,
                "tendencia": "stable",
            },
            "reviews_analizadas": 0,
            "topicos_con_alerta": 0,
        }


class TestRutaKpisMensual:
    @patch("routes.dashboard.obtener_kpis_mensual")
    def test_respuesta_ok(self, mock_svc, client, auth_headers):
        mock_svc.return_value = KPIS_MOCK
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["error"] is None
        assert data["data"] == KPIS_MOCK

    @patch("routes.dashboard.obtener_kpis_mensual")
    def test_llama_servicio_con_enteros(self, mock_svc, client, auth_headers):
        mock_svc.return_value = KPIS_MOCK
        client.get(f"{ENDPOINT}?hotel_id=5&anio=2026&mes=4", headers=auth_headers)
        mock_svc.assert_called_once_with(5, 2026, 4)

    def test_query_invalida_retorna_400(self, client, auth_headers):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2019&mes=13", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    @patch("routes.dashboard.obtener_kpis_mensual")
    def test_error_interno_retorna_500(self, mock_svc, client, auth_headers):
        mock_svc.side_effect = RuntimeError("fallo")
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 500
        assert data["error"]["codigo"] == "ERROR_INTERNO"

    def test_sin_token_retorna_401(self, client):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11")
        assert resp.status_code == 401
        assert resp.get_json()["error"]["codigo"] == "TOKEN_REQUERIDO"
