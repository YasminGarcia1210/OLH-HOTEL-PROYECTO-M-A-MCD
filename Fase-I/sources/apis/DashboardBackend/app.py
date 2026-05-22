import datetime
import logging

import db
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from psycopg2.extras import RealDictCursor

from config import Config
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.hoteles import hoteles_bp
from routes.topicos import topicos_bp
from routes.usuarios import usuarios_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _jwt_error(codigo: str, mensaje: str, status: int):
    return jsonify({"ok": False, "data": None, "error": {"codigo": codigo, "mensaje": mensaje}}), status


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = Config.UPLOAD_MAX_BYTES
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(minutes=Config.JWT_ACCESS_TOKEN_MINUTES)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = datetime.timedelta(days=Config.JWT_REFRESH_TOKEN_DAYS)

    CORS(app)

    jwt = JWTManager(app)

    # ── Error handlers JWT ────────────────────────────────────────────────────

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return _jwt_error("TOKEN_REQUERIDO", "Se requiere un token de autenticación Bearer.", 401)

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return _jwt_error("TOKEN_INVALIDO", "El token es inválido.", 401)

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return _jwt_error("TOKEN_EXPIRADO", "El token ha expirado.", 401)

    @jwt.revoked_token_loader
    def revoked_token(_header, _payload):
        return _jwt_error("TOKEN_REVOCADO", "El token ha sido revocado.", 401)

    @jwt.needs_fresh_token_loader
    def needs_fresh_token(_header, _payload):
        return _jwt_error("TOKEN_NO_FRESCO", "Se requiere un token reciente.", 401)

    # ── Blocklist ─────────────────────────────────────────────────────────────

    @jwt.token_in_blocklist_loader
    def check_if_revoked(_header, payload):
        jti = payload["jti"]
        user_id = payload.get("sub")
        try:
            with db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT 1 FROM token_blocklist WHERE jti = %s", (jti,))
                    if cur.fetchone() is not None:
                        return True
                    if user_id is not None:
                        cur.execute("SELECT activo FROM usuarios WHERE id = %s", (user_id,))
                        row = cur.fetchone()
                        if row is None or not row["activo"]:
                            return True
                    return False
        except Exception:
            return False

    # ── Blueprints ────────────────────────────────────────────────────────────

    db.init_pool(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(hoteles_bp)
    app.register_blueprint(topicos_bp)
    app.register_blueprint(usuarios_bp)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(
            {
                "ok": True,
                "service": Config.SERVICE_NAME,
                "version": Config.VERSION,
                "status": "up",
            }
        )

    @app.errorhandler(404)
    def not_found(e):
        return (
            jsonify(
                {
                    "ok": False,
                    "data": None,
                    "error": {"codigo": "RUTA_NO_ENCONTRADA", "mensaje": str(e)},
                }
            ),
            404,
        )

    @app.errorhandler(405)
    def method_not_allowed(e):
        return (
            jsonify(
                {
                    "ok": False,
                    "data": None,
                    "error": {"codigo": "METODO_NO_PERMITIDO", "mensaje": str(e)},
                }
            ),
            405,
        )

    @app.errorhandler(500)
    def internal_error(e):
        return (
            jsonify(
                {
                    "ok": False,
                    "data": None,
                    "error": {
                        "codigo": "ERROR_INTERNO",
                        "mensaje": "Error inesperado en el servidor",
                    },
                }
            ),
            500,
        )

    @app.errorhandler(413)
    def payload_too_large(_e):
        return (
            jsonify(
                {
                    "ok": False,
                    "data": None,
                    "error": {
                        "codigo": "ARCHIVO_DEMASIADO_GRANDE",
                        "mensaje": "El archivo supera el tamaño máximo permitido.",
                    },
                }
            ),
            413,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
