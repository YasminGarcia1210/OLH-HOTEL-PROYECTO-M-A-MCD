"""
Asegura que `metricas_read` (paquete editable en ../../libs/metricas_read) sea importable
al ejecutar pytest desde esta carpeta, incluso si el venv no tiene el -e instalado.

También expone el fixture `auth_headers` para incluir un JWT válido en tests de rutas.
"""

import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parents[1]
_libs_metricas = _root.parent / "libs" / "metricas_read"
if _libs_metricas.is_dir():
    sys.path.insert(0, str(_libs_metricas))


@pytest.fixture()
def auth_headers(client):
    """Devuelve headers HTTP con un access token de prueba (sin BD real)."""
    from flask_jwt_extended import create_access_token
    with client.application.app_context():
        token = create_access_token(identity="1", additional_claims={"username": "test_user"})
    return {"Authorization": f"Bearer {token}"}
