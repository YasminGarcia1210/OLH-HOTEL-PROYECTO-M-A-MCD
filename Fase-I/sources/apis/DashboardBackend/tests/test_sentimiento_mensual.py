"""
Tests de GET /api/v1/metricas/sentimiento-mensual.

Cubren:
- Validación de query params (validar_query_sentimiento_mensual).
- Cálculo del rango de meses (_rango_desde_meses) en el servicio.
- Mapeo HTTP: envelope, códigos de estado, mocks del servicio.
"""

from datetime import date
from unittest.mock import patch

import pytest

from app import create_app
from metricas_read.service import _rango_desde_meses
from routes.validators import validar_query_sentimiento_mensual

ENDPOINT = "/api/v1/metricas/sentimiento-mensual"

SERIE_MOCK = [
    {"anio": 2025, "mes": 10, "score_promedio": 65.00, "total_reviews": 620},
    {"anio": 2025, "mes": 11, "score_promedio": 68.40, "total_reviews": 812},
]


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestValidadorQuery:
    def test_valido_solo_hotel_id(self):
        assert validar_query_sentimiento_mensual({"hotel_id": "1"}) == []

    def test_valido_con_meses(self):
        assert validar_query_sentimiento_mensual({"hotel_id": "1", "meses": "6"}) == []

    def test_valido_con_rango(self):
        assert validar_query_sentimiento_mensual(
            {"hotel_id": "1", "desde": "2025-01", "hasta": "2025-11"}
        ) == []

    def test_hotel_id_faltante(self):
        errores = validar_query_sentimiento_mensual({})
        assert any("hotel_id" in e for e in errores)

    def test_hotel_id_no_entero(self):
        errores = validar_query_sentimiento_mensual({"hotel_id": "abc"})
        assert any("hotel_id" in e for e in errores)

    def test_hotel_id_negativo(self):
        errores = validar_query_sentimiento_mensual({"hotel_id": "-1"})
        assert any("hotel_id" in e for e in errores)

    def test_meses_fuera_de_rango_alto(self):
        errores = validar_query_sentimiento_mensual({"hotel_id": "1", "meses": "25"})
        assert any("meses" in e for e in errores)

    def test_meses_fuera_de_rango_bajo(self):
        errores = validar_query_sentimiento_mensual({"hotel_id": "1", "meses": "0"})
        assert any("meses" in e for e in errores)

    def test_meses_no_entero(self):
        errores = validar_query_sentimiento_mensual({"hotel_id": "1", "meses": "abc"})
        assert any("meses" in e for e in errores)

    def test_desde_sin_hasta(self):
        errores = validar_query_sentimiento_mensual({"hotel_id": "1", "desde": "2025-01"})
        assert any("hasta" in e for e in errores)

    def test_hasta_sin_desde(self):
        errores = validar_query_sentimiento_mensual({"hotel_id": "1", "hasta": "2025-11"})
        assert any("desde" in e for e in errores)

    def test_desde_formato_invalido(self):
        errores = validar_query_sentimiento_mensual(
            {"hotel_id": "1", "desde": "2025-13", "hasta": "2025-11"}
        )
        assert any("desde" in e for e in errores)

    def test_hasta_formato_invalido(self):
        errores = validar_query_sentimiento_mensual(
            {"hotel_id": "1", "desde": "2025-01", "hasta": "2025/11"}
        )
        assert any("hasta" in e for e in errores)

    def test_desde_posterior_a_hasta(self):
        errores = validar_query_sentimiento_mensual(
            {"hotel_id": "1", "desde": "2025-11", "hasta": "2025-01"}
        )
        assert any("posterior" in e for e in errores)


class TestRangoDesdeMeses:
    def test_un_mes(self):
        hoy = date(2026, 4, 14)
        with patch("metricas_read.service.date") as mock_date:
            mock_date.today.return_value = hoy
            desde_a, desde_m, hasta_a, hasta_m = _rango_desde_meses(1)
        assert (desde_a, desde_m) == (2026, 4)
        assert (hasta_a, hasta_m) == (2026, 4)

    def test_tres_meses(self):
        hoy = date(2026, 4, 14)
        with patch("metricas_read.service.date") as mock_date:
            mock_date.today.return_value = hoy
            desde_a, desde_m, hasta_a, hasta_m = _rango_desde_meses(3)
        assert (desde_a, desde_m) == (2026, 2)
        assert (hasta_a, hasta_m) == (2026, 4)

    def test_doce_meses(self):
        hoy = date(2026, 4, 14)
        with patch("metricas_read.service.date") as mock_date:
            mock_date.today.return_value = hoy
            desde_a, desde_m, hasta_a, hasta_m = _rango_desde_meses(12)
        assert (desde_a, desde_m) == (2025, 5)
        assert (hasta_a, hasta_m) == (2026, 4)

    def test_cruce_de_anio(self):
        hoy = date(2026, 3, 1)
        with patch("metricas_read.service.date") as mock_date:
            mock_date.today.return_value = hoy
            desde_a, desde_m, hasta_a, hasta_m = _rango_desde_meses(3)
        assert (desde_a, desde_m) == (2026, 1)
        assert (hasta_a, hasta_m) == (2026, 3)

    def test_cruce_de_anio_enero(self):
        hoy = date(2026, 1, 15)
        with patch("metricas_read.service.date") as mock_date:
            mock_date.today.return_value = hoy
            desde_a, desde_m, hasta_a, hasta_m = _rango_desde_meses(2)
        assert (desde_a, desde_m) == (2025, 12)
        assert (hasta_a, hasta_m) == (2026, 1)


class TestRutaSentimientoMensual:
    @patch("routes.dashboard.obtener_sentimiento_mensual")
    def test_respuesta_ok(self, mock_svc, client, auth_headers):
        mock_svc.return_value = SERIE_MOCK
        resp = client.get(f"{ENDPOINT}?hotel_id=1", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["error"] is None
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2

    @patch("routes.dashboard.obtener_sentimiento_mensual")
    def test_puntos_tienen_campos_correctos(self, mock_svc, client, auth_headers):
        mock_svc.return_value = SERIE_MOCK
        resp = client.get(f"{ENDPOINT}?hotel_id=1&meses=12", headers=auth_headers)
        data = resp.get_json()
        punto = data["data"][0]
        assert set(punto.keys()) == {"anio", "mes", "score_promedio", "total_reviews"}

    @patch("routes.dashboard.obtener_sentimiento_mensual")
    def test_llama_servicio_con_hotel_id_y_meses(self, mock_svc, client, auth_headers):
        mock_svc.return_value = []
        client.get(f"{ENDPOINT}?hotel_id=5&meses=6", headers=auth_headers)
        mock_svc.assert_called_once_with(5, meses=6, desde=None, hasta=None)

    @patch("routes.dashboard.obtener_sentimiento_mensual")
    def test_llama_servicio_con_rango(self, mock_svc, client, auth_headers):
        mock_svc.return_value = []
        client.get(f"{ENDPOINT}?hotel_id=2&desde=2025-01&hasta=2025-06", headers=auth_headers)
        mock_svc.assert_called_once_with(2, meses=None, desde="2025-01", hasta="2025-06")

    def test_sin_hotel_id_retorna_400(self, client, auth_headers):
        resp = client.get(ENDPOINT, headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    def test_hotel_id_invalido_retorna_400(self, client, auth_headers):
        resp = client.get(f"{ENDPOINT}?hotel_id=abc", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    def test_meses_fuera_de_rango_retorna_400(self, client, auth_headers):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&meses=99", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    def test_desde_sin_hasta_retorna_400(self, client, auth_headers):
        resp = client.get(f"{ENDPOINT}?hotel_id=1&desde=2025-01", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    @patch("routes.dashboard.obtener_sentimiento_mensual")
    def test_error_interno_retorna_500(self, mock_svc, client, auth_headers):
        mock_svc.side_effect = RuntimeError("fallo de bd")
        resp = client.get(f"{ENDPOINT}?hotel_id=1", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 500
        assert data["error"]["codigo"] == "ERROR_INTERNO"

    @patch("routes.dashboard.obtener_sentimiento_mensual")
    def test_lista_vacia_es_respuesta_valida(self, mock_svc, client, auth_headers):
        mock_svc.return_value = []
        resp = client.get(f"{ENDPOINT}?hotel_id=1", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["data"] == []

    def test_sin_token_retorna_401(self, client):
        resp = client.get(f"{ENDPOINT}?hotel_id=1")
        assert resp.status_code == 401
        assert resp.get_json()["error"]["codigo"] == "TOKEN_REQUERIDO"
