import logging
import re

import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from psycopg2 import errors as pg_errors

import db
from repositories import usuarios_repository

logger = logging.getLogger(__name__)

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/api/v1/usuarios")

_RE_USERNAME = re.compile(r"^[a-zA-Z0-9_.\-]{3,100}$")


def _ok(data, status=200):
    return jsonify({"ok": True, "data": data, "error": None}), status


def _error(codigo: str, mensaje: str, status: int = 400):
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


# ── GET /api/v1/usuarios ──────────────────────────────────────────────────────
@usuarios_bp.route("", methods=["GET"])
@jwt_required()
def list_usuarios():
    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = min(100, max(1, int(request.args.get("page_size", 20))))
    except (ValueError, TypeError):
        return _error("PARAMETROS_INVALIDOS", "page y page_size deben ser enteros.", 400)

    requester_hotel_id = get_jwt().get("hotel_id")

    try:
        with db.get_connection() as conn:
            total, rows = usuarios_repository.get_all_usuarios(conn, page, page_size, requester_hotel_id)
    except Exception:
        logger.error("Error de BD en GET /api/v1/usuarios", exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al obtener usuarios.", 500)

    return _ok({"items": rows, "total": total, "page": page, "page_size": page_size})


# ── GET /api/v1/usuarios/<id> ─────────────────────────────────────────────────
@usuarios_bp.route("/<int:usuario_id>", methods=["GET"])
@jwt_required()
def get_usuario(usuario_id):
    requester_hotel_id = get_jwt().get("hotel_id")

    try:
        with db.get_connection() as conn:
            usuario = usuarios_repository.get_usuario_by_id(conn, usuario_id, requester_hotel_id)
    except Exception:
        logger.error("Error de BD en GET /api/v1/usuarios/%s", usuario_id, exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al obtener el usuario.", 500)

    if usuario is None:
        return _error("USUARIO_NO_ENCONTRADO", f"No existe un usuario con id={usuario_id}.", 404)

    return _ok(usuario)


# ── POST /api/v1/usuarios ─────────────────────────────────────────────────────
@usuarios_bp.route("", methods=["POST"])
@jwt_required()
def create_usuario():
    body = request.get_json(silent=True) or {}
    requester_hotel_id = get_jwt().get("hotel_id")

    nombre = str(body.get("nombre", "")).strip()
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    hotel_id_raw = body.get("hotel_id")
    rol = str(body.get("rol", "viewer")).strip()

    errores = []

    if not nombre:
        errores.append("nombre es requerido.")
    elif len(nombre) > 120:
        errores.append("nombre no puede superar 120 caracteres.")

    if not username:
        errores.append("username es requerido.")
    elif not _RE_USERNAME.match(username):
        errores.append("username solo permite letras, números, puntos, guiones y guiones bajos (3-100 caracteres).")

    if not password:
        errores.append("password es requerido.")
    elif len(password) < 8:
        errores.append("password debe tener al menos 8 caracteres.")

    if rol not in ("admin", "viewer"):
        errores.append("rol debe ser 'admin' o 'viewer'.")

    hotel_id = None
    if hotel_id_raw is not None:
        try:
            hotel_id = int(hotel_id_raw)
            if hotel_id < 1:
                errores.append("hotel_id debe ser un entero positivo.")
        except (ValueError, TypeError):
            errores.append("hotel_id debe ser un entero positivo.")

    # Admins con hotel asignado solo pueden crear usuarios de su propio hotel.
    if requester_hotel_id is not None and hotel_id != int(requester_hotel_id):
        return _error("ACCESO_DENEGADO", "Solo puedes crear usuarios de tu hotel.", 403)

    if errores:
        return _error("PARAMETROS_INVALIDOS", " ".join(errores), 400)

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    try:
        with db.get_connection() as conn:
            nuevo = usuarios_repository.create_usuario(conn, nombre, username, password_hash, hotel_id, rol)
    except pg_errors.UniqueViolation:
        return _error("USERNAME_DUPLICADO", f"El username '{username}' ya está en uso.", 409)
    except Exception:
        logger.error("Error de BD en POST /api/v1/usuarios", exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al crear el usuario.", 500)

    logger.info("Usuario creado: username=%s id=%s", username, nuevo["id"])
    return _ok(nuevo, 201)


# ── PUT /api/v1/usuarios/<id> ─────────────────────────────────────────────────
@usuarios_bp.route("/<int:usuario_id>", methods=["PUT"])
@jwt_required()
def update_usuario(usuario_id):
    body = request.get_json(silent=True) or {}

    fields: dict = {}
    errores: list[str] = []

    if "nombre" in body:
        nombre = str(body["nombre"]).strip()
        if not nombre:
            errores.append("nombre no puede estar vacío.")
        elif len(nombre) > 120:
            errores.append("nombre no puede superar 120 caracteres.")
        else:
            fields["nombre"] = nombre

    if "username" in body:
        username = str(body["username"]).strip()
        if not _RE_USERNAME.match(username):
            errores.append("username solo permite letras, números, puntos, guiones y guiones bajos (3-100 caracteres).")
        else:
            fields["username"] = username

    if "password" in body:
        password = str(body["password"])
        if len(password) < 8:
            errores.append("password debe tener al menos 8 caracteres.")
        else:
            fields["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    if "hotel_id" in body:
        hid = body["hotel_id"]
        if hid is None:
            fields["hotel_id"] = None
        else:
            try:
                hid_int = int(hid)
                if hid_int < 1:
                    errores.append("hotel_id debe ser un entero positivo.")
                else:
                    fields["hotel_id"] = hid_int
            except (ValueError, TypeError):
                errores.append("hotel_id debe ser un entero positivo.")

    if "activo" in body:
        if not isinstance(body["activo"], bool):
            errores.append("activo debe ser un booleano.")
        else:
            fields["activo"] = body["activo"]

    if "rol" in body:
        if body["rol"] not in ("admin", "viewer"):
            errores.append("rol debe ser 'admin' o 'viewer'.")
        else:
            fields["rol"] = body["rol"]

    if errores:
        return _error("PARAMETROS_INVALIDOS", " ".join(errores), 400)

    if not fields:
        return _error("PARAMETROS_INVALIDOS", "No se proporcionaron campos para actualizar.", 400)

    requester_hotel_id = get_jwt().get("hotel_id")

    try:
        with db.get_connection() as conn:
            actualizado = usuarios_repository.update_usuario(conn, usuario_id, fields, requester_hotel_id)
    except pg_errors.UniqueViolation:
        return _error("USERNAME_DUPLICADO", "El username ya está en uso por otro usuario.", 409)
    except Exception:
        logger.error("Error de BD en PUT /api/v1/usuarios/%s", usuario_id, exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al actualizar el usuario.", 500)

    if actualizado is None:
        return _error("USUARIO_NO_ENCONTRADO", f"No existe un usuario con id={usuario_id}.", 404)

    logger.info("Usuario actualizado: id=%s", usuario_id)
    return _ok(actualizado)


# ── DELETE /api/v1/usuarios/<id> ──────────────────────────────────────────────
@usuarios_bp.route("/<int:usuario_id>", methods=["DELETE"])
@jwt_required()
def delete_usuario(usuario_id):
    requester_hotel_id = get_jwt().get("hotel_id")

    try:
        with db.get_connection() as conn:
            deleted = usuarios_repository.delete_usuario(conn, usuario_id, requester_hotel_id)
    except Exception:
        logger.error("Error de BD en DELETE /api/v1/usuarios/%s", usuario_id, exc_info=True)
        return _error("ERROR_INTERNO", "Error inesperado al eliminar el usuario.", 500)

    if not deleted:
        return _error("USUARIO_NO_ENCONTRADO", f"No existe un usuario con id={usuario_id}.", 404)

    logger.info("Usuario eliminado: id=%s", usuario_id)
    return _ok({"id": usuario_id, "eliminado": True})
