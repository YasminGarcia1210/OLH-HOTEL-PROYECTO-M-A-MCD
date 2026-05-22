import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

import db
from repositories import topicos_repository

logger = logging.getLogger(__name__)

topicos_bp = Blueprint("topicos", __name__, url_prefix="/api/v1/topicos")


def _ok(data, status=200):
    return jsonify({"ok": True, "data": data, "error": None}), status


def _error(codigo: str, mensaje: str, status: int = 400):
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ── GET /api/v1/topicos ───────────────────────────────────────────────────────
@topicos_bp.route("", methods=["GET"])
@jwt_required()
def list_topicos():
    try:
        with db.get_connection() as conn:
            topicos = topicos_repository.get_all_topicos(conn)
    except Exception:
        logger.error("Error de BD en GET /api/v1/topicos", exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al obtener tópicos.", 500)

    return _ok(topicos)


# ── PATCH /api/v1/topicos/<id> ────────────────────────────────────────────────
@topicos_bp.route("/<int:topico_id>", methods=["PATCH"])
@jwt_required()
def patch_topico(topico_id):
    body = request.get_json(silent=True) or {}

    if "umbral_alerta" not in body:
        return _error("PARAMETROS_INVALIDOS", "El campo 'umbral_alerta' es requerido.", 400)

    try:
        umbral = int(body["umbral_alerta"])
    except (ValueError, TypeError):
        return _error("PARAMETROS_INVALIDOS", "'umbral_alerta' debe ser un entero.", 400)

    if not (0 <= umbral <= 100):
        return _error("PARAMETROS_INVALIDOS", "'umbral_alerta' debe estar entre 0 y 100.", 400)

    try:
        with db.get_connection() as conn:
            topico = topicos_repository.update_umbral_alerta(conn, topico_id, umbral)
    except Exception:
        logger.error("Error de BD en PATCH /api/v1/topicos/%s", topico_id, exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al actualizar el tópico.", 500)

    if topico is None:
        return _error("TOPICO_NO_ENCONTRADO", f"No existe un tópico con id={topico_id}.", 404)

    logger.info("umbral_alerta actualizado: topico_id=%s umbral=%s", topico_id, umbral)
    return _ok(topico)
