"""Tests unitarios de helpers de prefijo en azure_blob_upload_service."""

from unittest.mock import patch

from services import azure_blob_upload_service as az


def test_blob_nivel_directo_raiz():
    assert az._blob_es_nivel_directo("informe.csv", "") is True
    assert az._blob_es_nivel_directo("sub/x.csv", "") is False
    assert az._blob_es_nivel_directo("", "") is False


def test_blob_nivel_directo_con_prefijo():
    assert az._blob_es_nivel_directo("entrada/datos.csv", "entrada/") is True
    assert az._blob_es_nivel_directo("entrada/sub/datos.csv", "entrada/") is False
    assert az._blob_es_nivel_directo("otro/datos.csv", "entrada/") is False


def test_prefijos_excluidos_parse():
    with patch.object(az.Config, "AZURE_BLOB_LIST_EXCLUDE_PREFIXES", "limpios, backup"):
        prefs = az._prefijos_excluidos_desde_config()
        assert "limpios/" in prefs
        assert "backup/" in prefs


def test_blob_excluido_limpios():
    prefs = ["limpios/"]
    assert az._blob_bajo_prefijo_excluido("limpios/resenas_hotel_clean.csv", prefs) is True
    assert az._blob_bajo_prefijo_excluido("entrada/x.csv", prefs) is False
