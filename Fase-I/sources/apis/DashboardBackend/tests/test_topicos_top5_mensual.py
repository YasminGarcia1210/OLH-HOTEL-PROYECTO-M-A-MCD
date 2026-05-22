"""
Tests de GET /api/v1/metricas/topicos/top5.

Cubren validación de query, envelope HTTP y delegación al servicio.
"""

from unittest.mock import patch

import pytest

from app import create_app
from metricas_read.service import obtener_topicos_top5_mensual

ENDPOINT = "/api/v1/metricas/topicos/top5"

TOP5_MOCK = [
    {"posicion": 1, "slug": "ruido", "nombre": "Ruido", "score_promedio": 52.3, "alerta": True},
    {"posicion": 2, "slug": "wifi", "nombre": "WiFi", "score_promedio": 58.1, "alerta": True},
]


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestRutaTopicosTop5Mensual:
    @patch("routes.dashboard.obtener_topicos_top5_mensual")
    def test_respuesta_ok(self, mock_svc, client, auth_headers):
        mock_svc.return_value = TOP5_MOCK
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["error"] is None
        assert data["data"] == TOP5_MOCK

    @patch("routes.dashboard.obtener_topicos_top5_mensual")
    def test_llama_servicio_con_enteros(self, mock_svc, client, auth_headers):
        mock_svc.return_value = []
        client.get(f"{ENDPOINT}?hotel_id=2&anio=2026&mes=4", headers=auth_headers)
        mock_svc.assert_called_once_with(2, 2026, 4)

    def test_query_invalida_retorna_400(self, client, auth_headers):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2019&mes=13", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    @patch("routes.dashboard.obtener_topicos_top5_mensual")
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


class TestServicioTopicosTop5Mensual:
    @patch("metricas_read.service.metricas_repo.listar_topicos_top5_mensual")
    def test_asigna_posicion_ordinal(self, mock_repo):
        mock_repo.return_value = [
            {"slug": "ruido", "nombre": "Ruido", "score_promedio": 52.3, "alerta": True},
            {"slug": "wifi", "nombre": "WiFi", "score_promedio": 58.1, "alerta": True},
        ]
        out = obtener_topicos_top5_mensual(1, 2025, 11)
        assert out == [
            {"posicion": 1, "slug": "ruido", "nombre": "Ruido", "score_promedio": 52.3, "alerta": True},
            {"posicion": 2, "slug": "wifi", "nombre": "WiFi", "score_promedio": 58.1, "alerta": True},
        ]
