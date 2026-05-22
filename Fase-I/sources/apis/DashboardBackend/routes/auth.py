import logging

import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from psycopg2.extras import RealDictCursor

import db

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _error(codigo: str, mensaje: str, status: int = 400):
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/login
#
# Body JSON: { "username": "...", "password": "..." }
# Respuesta: access_token (30 min) + refresh_token (30 días)
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))

    if not username or not password:
        return _error("PARAMETROS_INVALIDOS", "username y password son requeridos.", 400)

    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, password_hash, rol, hotel_id FROM usuarios"
                    " WHERE username = %s AND activo = TRUE",
                    (username,),
                )
                user = cur.fetchone()
    except Exception:
        logger.error("Error de BD en POST /api/v1/auth/login", exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al autenticar.", 500)

    if user is None or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return _error("CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos.", 401)

    identity = str(user["id"])
    additional_claims = {"username": user["username"], "rol": user["rol"], "hotel_id": user["hotel_id"]}

    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_claims)

    logger.info("Login exitoso: username=%s", username)
    return jsonify({
        "ok": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        },
        "error": None,
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/refresh
#
# Header: Authorization: Bearer <refresh_token>
# Respuesta: nuevo access_token
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    claims = get_jwt()

    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT activo FROM usuarios WHERE id = %s", (identity,))
                user = cur.fetchone()
    except Exception:
        logger.error("Error de BD en POST /api/v1/auth/refresh", exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al refrescar sesión.", 500)

    if user is None or not user["activo"]:
        return _error("USUARIO_INACTIVO", "La cuenta está desactivada.", 401)

    additional_claims = {"username": claims.get("username", ""), "rol": claims.get("rol", "viewer"), "hotel_id": claims.get("hotel_id")}
    new_access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    return jsonify({
        "ok": True,
        "data": {"access_token": new_access_token, "token_type": "Bearer"},
        "error": None,
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/logout
#
# Header : Authorization: Bearer <access_token>
# Body   : { "refresh_token": "..." }   (requerido)
# Revoca ambos tokens en una sola llamada.
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    access_jti = get_jwt()["jti"]

    body = request.get_json(silent=True) or {}
    raw_refresh = body.get("refresh_token", "")
    if not raw_refresh:
        return _error("PARAMETROS_INVALIDOS", "refresh_token es requerido en el body.", 400)

    try:
        refresh_payload = decode_token(raw_refresh)
    except Exception:
        return _error("TOKEN_INVALIDO", "El refresh_token es inválido.", 400)

    if refresh_payload.get("type") != "refresh":
        return _error("TOKEN_INVALIDO", "El token proporcionado no es un refresh token.", 400)

    refresh_jti = refresh_payload["jti"]

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO token_blocklist (jti, tipo) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    [(access_jti, "access"), (refresh_jti, "refresh")],
                )
    except Exception:
        logger.error("Error de BD en POST /api/v1/auth/logout", exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al cerrar sesión.", 500)

    logger.info("Logout: access_jti=%s refresh_jti=%s", access_jti, refresh_jti)
    return jsonify({"ok": True, "data": {"revocados": 2}, "error": None}), 200
