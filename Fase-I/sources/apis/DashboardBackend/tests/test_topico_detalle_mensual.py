"""
Tests de GET /api/v1/metricas/topicos/<slug>/detalle.

Cubren validación, lógica de servicio y mapeo HTTP.
"""

from unittest.mock import patch

import pytest

from app import create_app
from metricas_read.exceptions import TopicoNoEncontradoError
from metricas_read.service import obtener_topico_detalle_mensual
from routes.validators import validar_slug_topico

ENDPOINT = "/api/v1/metricas/topicos/ruido/detalle"

DETALLE_MOCK = {
    "slug": "ruido",
    "nombre": "Ruido",
    "score_promedio": 52.3,
    "cambio_pct_vs_anterior": -5.2,
    "alerta": True,
    "umbral_alerta": 65,
    "menciones": {"total": 310, "positivas": 82, "negativas": 193, "neutras": 35},
    "fragmentos_destacados": [
        {
            "sentimiento": "negativo",
            "fragmento": "Se escucha todo desde el pasillo.",
            "confianza": 0.912,
        }
    ],
}


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestValidadorSlugTopico:
    def test_slug_valido(self):
        assert validar_slug_topico("ruido") == []

    def test_slug_vacio(self):
        errores = validar_slug_topico("  ")
        assert any("slug" in e for e in errores)

    def test_slug_con_caracteres_invalidos(self):
        errores = validar_slug_topico("ruido-1")
        assert any("slug" in e for e in errores)


class TestServicioTopicoDetalleMensual:
    @patch("metricas_read.service.metricas_repo.listar_fragmentos_topico_destacados")
    @patch("metricas_read.service.metricas_repo.obtener_topico_detalle_mensual")
    def test_compone_payload_con_menciones_y_fragmentos(self, mock_detalle, mock_fragmentos):
        mock_detalle.return_value = {
            "topico_id": 7,
            "slug": "ruido",
            "nombre": "Ruido",
            "umbral_alerta": 65,
            "score_promedio": 52.3,
            "cambio_pct_vs_anterior": -5.2,
            "alerta": True,
            "total_menciones": 310,
            "menciones_positivas": 82,
            "menciones_negativas": 193,
            "menciones_neutras": 35,
        }
        mock_fragmentos.return_value = [
            {"sentimiento": "negativo", "fragmento": "f1", "confianza": 0.91}
        ]

        out = obtener_topico_detalle_mensual(1, "ruido", 2025, 11)

        assert out["slug"] == "ruido"
        assert out["menciones"]["total"] == 310
        assert out["fragmentos_destacados"][0]["confianza"] == 0.91
        mock_detalle.assert_called_once_with(1, "ruido", 2025, 11)
        mock_fragmentos.assert_called_once_with(1, "ruido", 2025, 11, limit=3)

    @patch("metricas_read.service.metricas_repo.obtener_topico_detalle_mensual")
    def test_topico_inexistente_lanza_error_dominio(self, mock_detalle):
        mock_detalle.return_value = None
        with pytest.raises(TopicoNoEncontradoError):
            obtener_topico_detalle_mensual(1, "inexistente", 2025, 11)


class TestRutaTopicoDetalleMensual:
    @patch("routes.dashboard.obtener_topico_detalle_mensual")
    def test_respuesta_ok(self, mock_svc, client, auth_headers):
        mock_svc.return_value = DETALLE_MOCK
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["error"] is None
        assert data["data"] == DETALLE_MOCK

    @patch("routes.dashboard.obtener_topico_detalle_mensual")
    def test_llama_servicio_con_parametros_normalizados(self, mock_svc, client, auth_headers):
        mock_svc.return_value = DETALLE_MOCK
        client.get("/api/v1/metricas/topicos/ruido/detalle?hotel_id=3&anio=2026&mes=4", headers=auth_headers)
        mock_svc.assert_called_once_with(3, "ruido", 2026, 4)

    def test_query_invalida_retorna_400(self, client, auth_headers):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2019&mes=13", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    @patch("routes.dashboard.obtener_topico_detalle_mensual")
    def test_topico_no_encontrado_retorna_404(self, mock_svc, client, auth_headers):
        mock_svc.side_effect = TopicoNoEncontradoError("El tópico 'ruido' no existe")
        resp = client.get(f"{ENDPOINT}?hotel_id=1&anio=2025&mes=11", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 404
        assert data["error"]["codigo"] == "TOPICO_NO_ENCONTRADO"

    @patch("routes.dashboard.obtener_topico_detalle_mensual")
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
