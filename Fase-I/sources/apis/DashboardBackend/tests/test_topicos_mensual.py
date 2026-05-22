"""
Tests de GET /api/v1/metricas/topicos.

Cubren validación de query, envelope HTTP y delegación al servicio.
"""

from unittest.mock import patch

import pytest

from app import create_app
from routes.validators import validar_query_topicos_mensual

ENDPOINT = "/api/v1/metricas/topicos"

TOPICOS_MOCK = [
    {
        "topico_id": 7,
        "slug": "ruido",
        "nombre": "Ruido",
        "tipo": "adicional",
        "score_promedio": 52.30,
        "cambio_pct_vs_anterior": -5.2,
        "total_menciones": 310,
        "alerta": True,
        "tendencia": "down",
    },
]


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestValidadorQueryTopicos:
    def test_valido_minimo(self):
        assert validar_query_topicos_mensual(
            {"hotel_id": "1", "anio": "2025", "mes": "11"}
        ) == []

    def test_valido_con_tipo(self):
        assert validar_query_topicos_mensual(
            {"hotel_id": "1", "anio": "2025", "mes": "3", "tipo": "clave"}
        ) == []

    def test_hotel_id_faltante(self):
        assert any("hotel_id" in e for e in validar_query_topicos_mensual({"anio": "2025", "mes": "1"}))

    def test_anio_faltante(self):
        assert any("anio" in e for e in validar_query_topicos_mensual({"hotel_id": "1", "mes": "1"}))

    def test_mes_faltante(self):
        assert any("mes" in e for e in validar_query_topicos_mensual({"hotel_id": "1", "anio": "2025"}))

    def test_mes_fuera_rango(self):
        errores = validar_query_topicos_mensual({"hotel_id": "1", "anio": "2025", "mes": "13"})
        assert any("mes" in e for e in errores)

    def test_tipo_invalido(self):
        errores = validar_query_topicos_mensual(
            {"hotel_id": "1", "anio": "2025", "mes": "1", "tipo": "otro"}
        )
        assert any("tipo" in e for e in errores)

    def test_solo_alertas_invalido(self):
        errores = validar_query_topicos_mensual(
            {"hotel_id": "1", "anio": "2025", "mes": "1", "solo_alertas": "quizas"}
        )
        assert any("solo_alertas" in e for e in errores)


class TestRutaTopicosMensual:
    @patch("routes.dashboard.obtener_topicos_mensual")
    def test_respuesta_ok(self, mock_svc, client, auth_headers):
        mock_svc.return_value = TOPICOS_MOCK
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["error"] is None
        assert data["data"] == TOPICOS_MOCK

    @patch("routes.dashboard.obtener_topicos_mensual")
    def test_llama_servicio_con_filtros(self, mock_svc, client, auth_headers):
        mock_svc.return_value = []
        client.get(f"{ENDPOINT}?hotel_id=2&anio=2024&mes=6&tipo=adicional&solo_alertas=true", headers=auth_headers)
        mock_svc.assert_called_once_with(2, 2024, 6, tipo="adicional", solo_alertas=True)

    def test_sin_params_requeridos_400(self, client, auth_headers):
        resp = client.get(ENDPOINT, headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    @patch("routes.dashboard.obtener_topicos_mensual")
    def test_error_interno_500(self, mock_svc, client, auth_headers):
        mock_svc.side_effect = RuntimeError("bd")
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 500
        assert data["error"]["codigo"] == "ERROR_INTERNO"

    def test_sin_token_retorna_401(self, client):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11")
        assert resp.status_code == 401
        assert resp.get_json()["error"]["codigo"] == "TOKEN_REQUERIDO"
