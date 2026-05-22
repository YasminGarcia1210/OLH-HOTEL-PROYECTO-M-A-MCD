import logging
import threading
import time

import db
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from routes.absa import absa_bp, init_service
from services.absa_service import ABSAService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _start_openai_batch_poller(absa_service: ABSAService, interval_sec: int) -> None:
    """Hilo daemon que invoca sincronizar_batches_pendientes periódicamente."""
    if interval_sec < 10:
        interval_sec = 10
    log = logging.getLogger("openai_batch_poller")

    def loop():
        while True:
            try:
                absa_service.sincronizar_batches_pendientes()
            except Exception:
                log.exception("Fallo al sincronizar batches OpenAI")
            time.sleep(interval_sec)

    t = threading.Thread(target=loop, daemon=True, name="OpenAIBatchPoller")
    t.start()
    logging.getLogger(__name__).info(
        "Poller OpenAI Batch activo (intervalo=%ss).", interval_sec,
    )


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    # ── Pool de conexiones ────────────────────────────────────
    db.init_pool(Config)

    # ── Modelo ABSA (se instancia una sola vez al arrancar) ───
    absa_service = ABSAService(Config)
    init_service(absa_service)

    if (
        Config.OPENAI_BATCH_POLL_ENABLED
        and Config.ABSA_MODEL_BACKEND == "llm"
        and Config.LLM_PROVIDER == "openai"
    ):
        _start_openai_batch_poller(absa_service, Config.OPENAI_BATCH_POLL_INTERVAL_SEC)

    # ── Blueprints ────────────────────────────────────────────
    app.register_blueprint(absa_bp)

    # ── Health check ──────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "ok":      True,
            "service": "absa-service",
            "version": "0.1.0",
            "status":  "up",
        })

    # ── 404 global ────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "ok":    False,
            "data":  None,
            "error": {"codigo": "RUTA_NO_ENCONTRADA", "mensaje": str(e)},
        }), 404

    # ── 405 global ────────────────────────────────────────────
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "ok":    False,
            "data":  None,
            "error": {"codigo": "METODO_NO_PERMITIDO", "mensaje": str(e)},
        }), 405

    # ── 500 global ────────────────────────────────────────────
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "ok":    False,
            "data":  None,
            "error": {"codigo": "ERROR_INTERNO", "mensaje": "Error inesperado en el servidor"},
        }), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
