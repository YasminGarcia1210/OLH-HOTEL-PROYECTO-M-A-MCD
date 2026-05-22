"""
Tests de la ruta POST /api/v1/metricas/calcular.

Verifican el mapeo HTTP de excepciones de dominio y el envelope { ok, data, error }.
Usan mocks para aislar completamente el servicio y la BD.
"""

from unittest.mock import patch

import pytest

from app import create_app
from services.exceptions import (
    ArchivoNoEncontradoError,
    EstadoInvalidoError,
    HotelNoAsignadoError,
    PeriodoNoEncontradoError,
    SinReviewsError,
)

ENDPOINT = "/api/v1/metricas/calcular"

PAYLOAD_OK = {"archivo_id": 1}

RESPUESTA_SERVICIO = {
    "archivo_id": 1,
    "estado": "completed",
    "periodos": [{"anio": 2025, "mes": 11}],
    "metricas_por_periodo": [
        {
            "periodo": {"anio": 2025, "mes": 11},
            "global": {
                "score_promedio": 68.40,
                "cambio_pct_vs_anterior": 2.60,
                "total_reviews": 812,
                "reviews_positivas": 555,
                "reviews_negativas": 177,
                "reviews_neutras": 80,
            },
            "alertas_generadas": [],
        }
    ],
    "fecha_metricas": "2025-11-15T10:05:00+00:00",
}


@pytest.fixture()
def client():
    """Cliente de prueba con pool de BD simulado."""
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Body inválido ─────────────────────────────────────────────────────────────

class TestBodyInvalido:
    def test_body_ausente(self, client):
        resp = client.post(ENDPOINT, content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["ok"] is False
        assert data["error"]["codigo"] == "BODY_INVALIDO"

    def test_archivo_id_faltante(self, client):
        resp = client.post(ENDPOINT, json={})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "BODY_INVALIDO"

    def test_archivo_id_no_entero(self, client):
        resp = client.post(ENDPOINT, json={"archivo_id": "abc"})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "BODY_INVALIDO"

    def test_archivo_id_negativo(self, client):
        resp = client.post(ENDPOINT, json={"archivo_id": -1})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "BODY_INVALIDO"


# ── Excepciones de dominio ────────────────────────────────────────────────────

class TestExcepcionesDominio:
    @patch("routes.metricas.calcular_metricas")
    def test_archivo_no_encontrado(self, mock_svc, client):
        mock_svc.side_effect = ArchivoNoEncontradoError("archivo_id=99 no encontrado")
        resp = client.post(ENDPOINT, json=PAYLOAD_OK)
        data = resp.get_json()
        assert resp.status_code == 404
        assert data["error"]["codigo"] == "ARCHIVO_NO_ENCONTRADO"

    @patch("routes.metricas.calcular_metricas")
    def test_hotel_no_asignado(self, mock_svc, client):
        mock_svc.side_effect = HotelNoAsignadoError("sin hotel_id")
        resp = client.post(ENDPOINT, json=PAYLOAD_OK)
        data = resp.get_json()
        assert resp.status_code == 422
        assert data["error"]["codigo"] == "HOTEL_NO_ASIGNADO"

    @patch("routes.metricas.calcular_metricas")
    def test_estado_invalido(self, mock_svc, client):
        mock_svc.side_effect = EstadoInvalidoError("estado 'cleaned' no es 'topics_identified'")
        resp = client.post(ENDPOINT, json=PAYLOAD_OK)
        data = resp.get_json()
        assert resp.status_code == 409
        assert data["error"]["codigo"] == "ESTADO_INVALIDO"

    @patch("routes.metricas.calcular_metricas")
    def test_sin_reviews(self, mock_svc, client):
        mock_svc.side_effect = SinReviewsError("sin reviews")
        resp = client.post(ENDPOINT, json=PAYLOAD_OK)
        data = resp.get_json()
        assert resp.status_code == 422
        assert data["error"]["codigo"] == "SIN_REVIEWS"

    @patch("routes.metricas.calcular_metricas")
    def test_error_inesperado(self, mock_svc, client):
        mock_svc.side_effect = RuntimeError("fallo inesperado")
        resp = client.post(ENDPOINT, json=PAYLOAD_OK)
        data = resp.get_json()
        assert resp.status_code == 500
        assert data["error"]["codigo"] == "ERROR_INTERNO"


# ── Respuesta exitosa ─────────────────────────────────────────────────────────

class TestRespuestaExitosa:
    @patch("routes.metricas.calcular_metricas")
    def test_envelope_ok(self, mock_svc, client):
        mock_svc.return_value = RESPUESTA_SERVICIO
        resp = client.post(ENDPOINT, json=PAYLOAD_OK)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["error"] is None
        assert data["data"]["estado"] == "completed"

    @patch("routes.metricas.calcular_metricas")
    def test_periodos_en_respuesta(self, mock_svc, client):
        mock_svc.return_value = RESPUESTA_SERVICIO
        resp = client.post(ENDPOINT, json=PAYLOAD_OK)
        data = resp.get_json()
        assert len(data["data"]["periodos"]) == 1
        assert data["data"]["periodos"][0] == {"anio": 2025, "mes": 11}

    @patch("routes.metricas.calcular_metricas")
    def test_servicio_recibe_archivo_id(self, mock_svc, client):
        mock_svc.return_value = RESPUESTA_SERVICIO
        client.post(ENDPOINT, json={"archivo_id": 42})
        mock_svc.assert_called_once_with(42)


ENDPOINT_RECALC = "/api/v1/metricas/recalcular"

PAYLOAD_RECALC_OK = {"hotel_id": 1, "anio": 2025, "mes": 11}

RESPUESTA_RECALC = {
    "periodo": {"anio": 2025, "mes": 11},
    "hotel_id": 1,
    "global": {
        "score_promedio": 68.41,
        "cambio_pct_vs_anterior": 2.60,
        "total_reviews": 812,
        "reviews_positivas": 555,
        "reviews_negativas": 177,
        "reviews_neutras": 80,
    },
    "alertas_generadas": [],
    "fecha_metricas": "2025-11-15T10:05:00+00:00",
}


class TestRecalcularBodyInvalido:
    def test_body_ausente(self, client):
        resp = client.post(ENDPOINT_RECALC, content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["ok"] is False
        assert data["error"]["codigo"] == "BODY_INVALIDO"

    def test_hotel_id_faltante(self, client):
        resp = client.post(ENDPOINT_RECALC, json={"anio": 2025, "mes": 11})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "BODY_INVALIDO"

    def test_mes_fuera_rango(self, client):
        resp = client.post(ENDPOINT_RECALC, json={"hotel_id": 1, "anio": 2025, "mes": 13})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "BODY_INVALIDO"

    def test_anio_menor_2000(self, client):
        resp = client.post(ENDPOINT_RECALC, json={"hotel_id": 1, "anio": 1999, "mes": 6})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["codigo"] == "BODY_INVALIDO"


class TestRecalcularExcepciones:
    @patch("routes.metricas.recalcular_periodo")
    def test_periodo_no_encontrado(self, mock_svc, client):
        mock_svc.side_effect = PeriodoNoEncontradoError("no hay fila")
        resp = client.post(ENDPOINT_RECALC, json=PAYLOAD_RECALC_OK)
        data = resp.get_json()
        assert resp.status_code == 404
        assert data["error"]["codigo"] == "PERIODO_NO_ENCONTRADO"

    @patch("routes.metricas.recalcular_periodo")
    def test_error_inesperado(self, mock_svc, client):
        mock_svc.side_effect = RuntimeError("fallo")
        resp = client.post(ENDPOINT_RECALC, json=PAYLOAD_RECALC_OK)
        data = resp.get_json()
        assert resp.status_code == 500
        assert data["error"]["codigo"] == "ERROR_INTERNO"


class TestRecalcularExitoso:
    @patch("routes.metricas.recalcular_periodo")
    def test_envelope_ok(self, mock_svc, client):
        mock_svc.return_value = RESPUESTA_RECALC
        resp = client.post(ENDPOINT_RECALC, json=PAYLOAD_RECALC_OK)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["data"]["hotel_id"] == 1
        assert data["data"]["global"]["score_promedio"] == 68.41

    @patch("routes.metricas.recalcular_periodo")
    def test_servicio_recibe_argumentos(self, mock_svc, client):
        mock_svc.return_value = RESPUESTA_RECALC
        client.post(ENDPOINT_RECALC, json={"hotel_id": 7, "anio": 2024, "mes": 3})
        mock_svc.assert_called_once_with(7, 2024, 3)
