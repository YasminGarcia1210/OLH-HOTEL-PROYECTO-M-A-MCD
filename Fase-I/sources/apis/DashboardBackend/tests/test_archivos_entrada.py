"""
Tests de GET /api/v1/metricas/archivos/entrada.
"""

from unittest.mock import patch

import pytest

from app import create_app

ENDPOINT = "/api/v1/metricas/archivos/entrada"


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@patch("routes.dashboard.obtener_estado_archivos_entrada")
def test_ok_sin_limite(mock_svc, client, auth_headers):
    mock_svc.return_value = {
        "prefijo": "entrada",
        "pendientes": [
            {
                "blob_path": "entrada/nuevo.csv",
                "tamano_bytes": 10,
                "ultima_modificacion": None,
            }
        ],
        "en_pipeline": [],
    }
    rv = client.get(ENDPOINT, headers=auth_headers)
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["ok"] is True
    assert body["data"]["prefijo"] == "entrada"
    assert len(body["data"]["pendientes"]) == 1
    mock_svc.assert_called_once_with(
        limite=None,
        pipeline_page=1,
        pipeline_page_size=20,
        pendientes_page=1,
        pendientes_page_size=20,
    )


@patch("routes.dashboard.obtener_estado_archivos_entrada")
def test_ok_con_limite(mock_svc, client, auth_headers):
    mock_svc.return_value = {
        "prefijo": "entrada",
        "pendientes": [],
        "en_pipeline": [],
        "truncado": False,
    }
    rv = client.get(ENDPOINT + "?limite=100", headers=auth_headers)
    assert rv.status_code == 200
    mock_svc.assert_called_once_with(
        limite=100,
        pipeline_page=1,
        pipeline_page_size=20,
        pendientes_page=1,
        pendientes_page_size=20,
    )


def test_400_limite_invalido(client, auth_headers):
    rv = client.get(ENDPOINT + "?limite=0", headers=auth_headers)
    assert rv.status_code == 400
    assert rv.get_json()["error"]["codigo"] == "PARAMETROS_INVALIDOS"


def test_400_limite_demasiado_grande(client, auth_headers):
    rv = client.get(ENDPOINT + "?limite=99999", headers=auth_headers)
    assert rv.status_code == 400
    assert rv.get_json()["error"]["codigo"] == "PARAMETROS_INVALIDOS"


@patch("routes.dashboard.obtener_estado_archivos_entrada")
def test_400_configuracion(mock_svc, client, auth_headers):
    from services.exceptions import ConfiguracionEntradaError

    mock_svc.side_effect = ConfiguracionEntradaError("AZURE_BLOB_PREFIX_UPLOAD no está definido o está vacío.")
    rv = client.get(ENDPOINT, headers=auth_headers)
    assert rv.status_code == 400
    assert rv.get_json()["error"]["codigo"] == "CONFIGURACION_INCOMPLETA"


def test_sin_token_retorna_401(client):
    rv = client.get(ENDPOINT)
    assert rv.status_code == 401
    assert rv.get_json()["error"]["codigo"] == "TOKEN_REQUERIDO"
