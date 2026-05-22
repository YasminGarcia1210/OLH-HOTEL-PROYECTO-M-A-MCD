import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY  = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV   = os.getenv("FLASK_ENV", "development")
    DEBUG       = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    PORT        = int(os.getenv("PORT", 5001))

    # Base de datos
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = int(os.getenv("DB_PORT", 5432))
    DB_NAME     = os.getenv("DB_NAME", "olh_sentiment")
    DB_USER     = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # SSL (requerido por Neon y otros proveedores cloud)
    DB_SSLMODE  = os.getenv("DB_SSLMODE", "require")

    # Pool de conexiones
    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", 1))   # conexiones mínimas en reposo
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", 10))  # conexiones máximas simultáneas

    # Azure Blob Storage (CSV origen / limpio / procesados)
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_STORAGE_CONTAINER         = os.getenv("AZURE_STORAGE_CONTAINER", "")
    AZURE_BLOB_PREFIX_LIMPIOS       = os.getenv("AZURE_BLOB_PREFIX_LIMPIOS", "")
    AZURE_BLOB_PREFIX_PROCESADOS    = os.getenv("AZURE_BLOB_PREFIX_PROCESADOS", "")
