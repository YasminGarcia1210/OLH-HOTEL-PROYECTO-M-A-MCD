import logging

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

import db
from repositories import hoteles_repository

logger = logging.getLogger(__name__)

hoteles_bp = Blueprint("hoteles", __name__, url_prefix="/api/v1/hoteles")


def _ok(data):
    return jsonify({"ok": True, "data": data, "error": None}), 200


def _error(codigo: str, mensaje: str, status: int = 500):
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ── GET /api/v1/hoteles ───────────────────────────────────────────────────────
@hoteles_bp.route("", methods=["GET"])
@jwt_required()
def list_hoteles():
    try:
        with db.get_connection() as conn:
            hoteles = hoteles_repository.get_all_hoteles(conn)
    except Exception:
        logger.error("Error de BD en GET /api/v1/hoteles", exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al obtener hoteles.")

    return _ok(hoteles)
