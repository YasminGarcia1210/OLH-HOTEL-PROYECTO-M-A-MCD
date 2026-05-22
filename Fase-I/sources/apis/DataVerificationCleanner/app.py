import logging

from flask import Flask, jsonify
from flask_cors import CORS

import db
from config import Config
from routes.verificacion import verificacion_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    # ── Pool de conexiones ────────────────────────────────────
    db.init_pool(Config)

    @app.teardown_appcontext
    def cerrar_pool(exc):
        pass  # El pool es persistente; se cierra solo al detener el proceso

    # ── Blueprints ────────────────────────────────────────────
    app.register_blueprint(verificacion_bp)

    # ── Health check ──────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "ok":      True,
            "service": "data-verification-cleaner",
            "version": "1.0.0",
            "status":  "up"
        })

    # ── 404 global ────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "ok":    False,
            "data":  None,
            "error": {"codigo": "RUTA_NO_ENCONTRADA", "mensaje": str(e)}
        }), 404

    # ── 405 global ────────────────────────────────────────────
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "ok":    False,
            "data":  None,
            "error": {"codigo": "METODO_NO_PERMITIDO", "mensaje": str(e)}
        }), 405

    # ── 500 global ────────────────────────────────────────────
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "ok":    False,
            "data":  None,
            "error": {"codigo": "ERROR_INTERNO", "mensaje": "Error inesperado en el servidor"}
        }), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
