import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    PORT = int(os.getenv("PORT", 5002))
    SERVICE_NAME = os.getenv("SERVICE_NAME", "dashboard-backend")
    VERSION = os.getenv("APP_VERSION", "0.2.0")

    # Base de datos
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = int(os.getenv("DB_PORT", 5432))
    DB_NAME     = os.getenv("DB_NAME", "olh_sentiment")
    DB_USER     = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    DB_SSLMODE  = os.getenv("DB_SSLMODE", "require")

    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", 1))
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", 10))

    # Azure Blob Storage (subida desde dashboard)
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "")
    AZURE_BLOB_PREFIX_UPLOAD = os.getenv("AZURE_BLOB_PREFIX_UPLOAD", "")
    # GET archivos/entrada: prefijos virtuales a excluir del listado (coma). Por defecto `limpios` (salida del pipeline).
    # En .env usa AZURE_BLOB_LIST_EXCLUDE_PREFIXES= para no excluir ninguna ruta.
    AZURE_BLOB_LIST_EXCLUDE_PREFIXES = os.getenv("AZURE_BLOB_LIST_EXCLUDE_PREFIXES", "limpios")

    # Límite de tamaño de multipart (bytes); por defecto 50 MiB
    UPLOAD_MAX_BYTES = int(os.getenv("UPLOAD_MAX_BYTES", str(50 * 1024 * 1024)))

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", 30))
    JWT_REFRESH_TOKEN_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_DAYS", 30))

    # MetricProcessor (POST /api/v1/metricas/recalcular) — orquestación desde DashboardBackend
    METRIC_PROCESSOR_URL = os.getenv("METRIC_PROCESSOR_URL", "http://localhost:5004").rstrip("/")
    METRIC_PROCESSOR_TIMEOUT_SECONDS = int(os.getenv("METRIC_PROCESSOR_TIMEOUT_SECONDS", "30"))
