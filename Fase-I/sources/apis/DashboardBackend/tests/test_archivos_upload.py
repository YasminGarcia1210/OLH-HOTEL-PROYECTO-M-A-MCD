"""
Tests de POST /api/v1/metricas/archivos/upload y validador asociado.
"""

import io
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from routes.validators import validar_upload_archivo
from services.exceptions import ArchivoDuplicadoError

ENDPOINT = "/api/v1/metricas/archivos/upload"


@pytest.fixture()
def client():
    with patch("db.init_pool"):
        app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestValidarUploadArchivo:
    def test_sin_archivo(self):
        assert "obligatorio" in " ".join(validar_upload_archivo(None)).lower()

    def test_sin_nombre(self):
        f = MagicMock()
        f.filename = ""
        assert any("nombre" in e.lower() for e in validar_upload_archivo(f))

    def test_valido(self):
        f = MagicMock()
        f.filename = "data.csv"
        assert validar_upload_archivo(f) == []


class TestPostArchivoUpload:
    @patch("routes.dashboard.subir_archivo_dashboard")
    def test_ok(self, mock_subir, client, auth_headers):
        mock_subir.return_value = {
            "blob_path": "entrada/test.csv",
            "hash": "abc" * 10 + "ab",
            "nombre_archivo": "test.csv",
        }
        data = {
            "archivo": (io.BytesIO(b"a,b\n1,2"), "test.csv"),
        }
        rv = client.post(
            ENDPOINT,
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers,
        )
        assert rv.status_code == 200
        body = rv.get_json()
        assert body["ok"] is True
        assert body["data"]["blob_path"] == "entrada/test.csv"
        mock_subir.assert_called_once()

    @patch("routes.dashboard.subir_archivo_dashboard")
    def test_409_hash_duplicado(self, mock_subir, client, auth_headers):
        mock_subir.side_effect = ArchivoDuplicadoError("deadbeef")
        data = {"archivo": (io.BytesIO(b"x"), "x.csv")}
        rv = client.post(ENDPOINT, data=data, content_type="multipart/form-data", headers=auth_headers)
        assert rv.status_code == 409
        body = rv.get_json()
        assert body["ok"] is False
        assert body["error"]["codigo"] == "ARCHIVO_YA_SUBIDO"

    def test_400_sin_archivo(self, client, auth_headers):
        rv = client.post(ENDPOINT, data={}, content_type="multipart/form-data", headers=auth_headers)
        assert rv.status_code == 400
        assert rv.get_json()["error"]["codigo"] == "PARAMETROS_INVALIDOS"

    def test_sin_token_retorna_401(self, client):
        data = {"archivo": (io.BytesIO(b"a,b\n1,2"), "test.csv")}
        rv = client.post(ENDPOINT, data=data, content_type="multipart/form-data")
        assert rv.status_code == 401
        assert rv.get_json()["error"]["codigo"] == "TOKEN_REQUERIDO"
