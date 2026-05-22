"""
Tests de GET /api/v1/metricas/alertas.

Cubren validación de query, lógica de servicio y mapeo HTTP.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app import create_app
from metricas_read.service import obtener_alertas
from routes.validators import validar_query_alertas

ENDPOINT = "/api/v1/metricas/alertas"

ALERTAS_MOCK = [
    {
        "alerta_id": 6,
        "topico_slug": "ruido",
        "topico_nombre": "Ruido",
        "anio": 2025,
        "mes": 11,
        "score_actual": 52.3,
        "umbral_usado": 65,
        "mensaje": "Score de Ruido cayó a 52.3%, por debajo del umbral de 65%.",
        "generada_en": "2025-11-15T10:05:00Z",
    }
]


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestValidadorQueryAlertas:
    def test_valido_minimo(self):
        assert validar_query_alertas({"hotel_id": "1"}) == []

    def test_valido_con_resuelta(self):
        assert validar_query_alertas({"hotel_id": "1", "resuelta": "true"}) == []

    def test_hotel_id_faltante(self):
        errores = validar_query_alertas({})
        assert any("hotel_id" in e for e in errores)

    def test_hotel_id_invalido(self):
        errores = validar_query_alertas({"hotel_id": "abc"})
        assert any("hotel_id" in e for e in errores)

    def test_resuelta_invalido(self):
        errores = validar_query_alertas({"hotel_id": "1", "resuelta": "quizas"})
        assert any("resuelta" in e for e in errores)


class TestServicioAlertas:
    @patch("metricas_read.service.metricas_repo.listar_alertas")
    def test_serializa_fecha_en_iso_z(self, mock_repo):
        mock_repo.return_value = [
            {
                "alerta_id": 5,
                "topico_slug": "wifi",
                "topico_nombre": "WiFi",
                "anio": 2025,
                "mes": 11,
                "score_actual": 58.1,
                "umbral_usado": 65,
                "mensaje": "mensaje",
                "generada_en": datetime(2025, 11, 15, 10, 5, 0, tzinfo=timezone.utc),
            }
        ]
        out = obtener_alertas(1, resuelta=False)
        assert out[0]["generada_en"] == "2025-11-15T10:05:00Z"

    @patch("metricas_read.service.metricas_repo.listar_alertas")
    def test_delega_con_filtro_resuelta(self, mock_repo):
        mock_repo.return_value = []
        out = obtener_alertas(3, resuelta=True)
        assert out == []
        mock_repo.assert_called_once_with(3, resuelta=True)


class TestRutaAlertas:
    @patch("routes.dashboard.obtener_alertas")
    def test_respuesta_ok(self, mock_svc, client, auth_headers):
        mock_svc.return_value = ALERTAS_MOCK
        resp = client.get(f"{ENDPOINT}?hotel_id=1&resuelta=false", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["error"] is None
        assert data["data"] == ALERTAS_MOCK

    @patch("routes.dashboard.obtener_alertas")
    def test_llama_servicio_con_filtro_true(self, mock_svc, client, auth_headers):
        mock_svc.return_value = []
        client.get(f"{ENDPOINT}?hotel_id=8&resuelta=true", headers=auth_headers)
        mock_svc.assert_called_once_with(8, resuelta=True)

    def test_query_invalida_retorna_400(self, client, auth_headers):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&resuelta=invalid", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    @patch("routes.dashboard.obtener_alertas")
    def test_error_interno_retorna_500(self, mock_svc, client, auth_headers):
        mock_svc.side_effect = RuntimeError("fallo")
        resp = client.get(f"{ENDPOINT}?hotel_id=1&resuelta=false", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 500
        assert data["error"]["codigo"] == "ERROR_INTERNO"

    def test_sin_token_retorna_401(self, client):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&resuelta=false")
        assert resp.status_code == 401
        assert resp.get_json()["error"]["codigo"] == "TOKEN_REQUERIDO"
