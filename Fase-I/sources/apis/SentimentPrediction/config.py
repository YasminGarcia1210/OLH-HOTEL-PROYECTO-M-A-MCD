import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    PORT = int(os.getenv("PORT", 5003))

    # Base de datos
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "olh_sentiment")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_SSLMODE = os.getenv("DB_SSLMODE", "require")
    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", 1))
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", 10))

    # Modelo: ruta local (config + model.safetensors + tokenizer) o id Hugging Face `org/repo`
    SENTIMENT_MODEL_DIR = os.getenv("SENTIMENT_MODEL_DIR") or str(_BASE_DIR / "models" / "p91")
    SENTIMENT_MODEL_VERSION = os.getenv("SENTIMENT_MODEL_VERSION", "p91")
    SENTIMENT_BATCH_SIZE = int(os.getenv("SENTIMENT_BATCH_SIZE", "8"))
    SENTIMENT_DEVICE = os.getenv("SENTIMENT_DEVICE", "cpu")
    # Límite de caracteres para POST /sentimiento/predecir (texto plano antes de tokenizar)
    SENTIMENT_MAX_INPUT_CHARS = int(os.getenv("SENTIMENT_MAX_INPUT_CHARS", "8000"))
