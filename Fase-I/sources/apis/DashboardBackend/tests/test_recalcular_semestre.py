"""
Tests de POST /api/v1/metricas/recalcular-semestre.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from app import create_app
from routes.validators import validar_body_recalcular_semestre
from services.exceptions import MetricProcessorIndisponibleError
from services.metricas_recalculo_service import recalcular_semestre

ENDPOINT = "/api/v1/metricas/recalcular-semestre"


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestValidadorBodyRecalcularSemestre:
    def test_valido(self):
        assert validar_body_recalcular_semestre({"hotel_id": 1}) == []

    def test_body_vacio(self):
        assert any("vacío" in e for e in validar_body_recalcular_semestre({}))

    def test_hotel_id_faltante(self):
        errores = validar_body_recalcular_semestre({"foo": 1})
        assert any("hotel_id" in e for e in errores)

    def test_hotel_id_no_entero(self):
        errores = validar_body_recalcular_semestre({"hotel_id": "x"})
        assert any("hotel_id" in e for e in errores)

    def test_hotel_id_bool_rechazado(self):
        errores = validar_body_recalcular_semestre({"hotel_id": True})
        assert any("hotel_id" in e for e in errores)

    def test_hotel_id_cero(self):
        errores = validar_body_recalcular_semestre({"hotel_id": 0})
        assert any("hotel_id" in e for e in errores)


class TestServicioRecalcularSemestre:
    @patch("services.metricas_recalculo_service.Config.METRIC_PROCESSOR_URL", "http://mp")
    @patch("services.metricas_recalculo_service.Config.METRIC_PROCESSOR_TIMEOUT_SECONDS", 10)
    @patch("services.metricas_recalculo_service.requests.post")
    def test_seis_llamadas_orden_ascendente(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        ref = date(2026, 5, 12)
        out = recalcular_semestre(1, fecha_referencia=ref)

        assert mock_post.call_count == 6
        calls = [c.kwargs["json"] for c in mock_post.call_args_list]
        assert calls[0] == {"hotel_id": 1, "anio": 2025, "mes": 12}
        assert calls[-1] == {"hotel_id": 1, "anio": 2026, "mes": 5}
        assert out["hotel_id"] == 1
        assert out["primer_periodo"] == {"anio": 2025, "mes": 12}
        assert out["ultimo_periodo"] == {"anio": 2026, "mes": 5}
        assert out["periodos_solicitados"] == 6
        assert out["exitos"] == 6
        assert out["fallos"] == 0
        assert out["fallidos"] == []
        assert "fecha_inicio" in out and "fecha_fin" in out

    @patch("services.metricas_recalculo_service.Config.METRIC_PROCESSOR_URL", "http://mp")
    @patch("services.metricas_recalculo_service.Config.METRIC_PROCESSOR_TIMEOUT_SECONDS", 10)
    @patch("services.metricas_recalculo_service.requests.post")
    def test_un_periodo_404_acumula_fallo(self, mock_post):
        def side_effect(*_args, **_kwargs):
            r = MagicMock()
            mes = side_effect.n
            side_effect.n += 1
            if mes == 0:
                r.status_code = 404
                r.json.return_value = {
                    "ok": False,
                    "data": None,
                    "error": {"codigo": "PERIODO_NO_ENCONTRADO", "mensaje": "no hay"},
                }
                r.text = ""
            else:
                r.status_code = 200
            return r

        side_effect.n = 0
        mock_post.side_effect = side_effect

        ref = date(2026, 5, 12)
        out = recalcular_semestre(2, fecha_referencia=ref)

        assert out["exitos"] == 5
        assert out["fallos"] == 1
        assert len(out["fallidos"]) == 1
        f = out["fallidos"][0]
        assert f["anio"] == 2025 and f["mes"] == 12
        assert f["http_status"] == 404
        assert f["codigo"] == "PERIODO_NO_ENCONTRADO"

    @patch("services.metricas_recalculo_service.Config.METRIC_PROCESSOR_URL", "http://mp")
    @patch("services.metricas_recalculo_service.requests.post")
    def test_timeout_lanza_metric_processor_indisponible(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("t")

        with pytest.raises(MetricProcessorIndisponibleError):
            recalcular_semestre(1, fecha_referencia=date(2026, 5, 12))

    @patch("services.metricas_recalculo_service.Config.METRIC_PROCESSOR_URL", "http://mp")
    @patch("services.metricas_recalculo_service.requests.post")
    def test_connection_error_lanza(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("c")

        with pytest.raises(MetricProcessorIndisponibleError):
            recalcular_semestre(1, fecha_referencia=date(2026, 5, 12))


class TestRutaRecalcularSemestre:
    @patch("routes.dashboard.recalcular_semestre")
    def test_200_envelope(self, mock_svc, client, auth_headers):
        mock_svc.return_value = {
            "hotel_id": 1,
            "primer_periodo": {"anio": 2025, "mes": 12},
            "ultimo_periodo": {"anio": 2026, "mes": 5},
            "periodos_solicitados": 6,
            "exitos": 6,
            "fallos": 0,
            "fallidos": [],
            "fecha_inicio": "2026-05-12T00:00:00+00:00",
            "fecha_fin": "2026-05-12T00:00:01+00:00",
        }
        resp = client.post(
            ENDPOINT,
            json={"hotel_id": 1},
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["data"]["exitos"] == 6
        mock_svc.assert_called_once_with(1)

    def test_400_body_invalido(self, client, auth_headers):
        resp = client.post(
            ENDPOINT,
            json={"hotel_id": 0},
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["codigo"] == "BODY_INVALIDO"

    @patch("routes.dashboard.recalcular_semestre")
    def test_503_metric_processor(self, mock_svc, client, auth_headers):
        mock_svc.side_effect = MetricProcessorIndisponibleError("caído")
        resp = client.post(
            ENDPOINT,
            json={"hotel_id": 1},
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert resp.status_code == 503
        assert resp.get_json()["error"]["codigo"] == "METRIC_PROCESSOR_INDISPONIBLE"

    def test_401_sin_token(self, client):
        resp = client.post(ENDPOINT, json={"hotel_id": 1})
        assert resp.status_code == 401
