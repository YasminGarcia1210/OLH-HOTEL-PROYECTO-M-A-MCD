import os
from dotenv import load_dotenv

load_dotenv()


def _parse_laplace_prior_m() -> float:
    raw = os.getenv("LAPLACE_PRIOR_M", "0.6")
    v = float(raw)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"LAPLACE_PRIOR_M must be in [0, 1], got {v!r}")
    return v


def _parse_laplace_prior_c() -> float:
    raw = os.getenv("LAPLACE_PRIOR_C", "5")
    v = float(raw)
    if v < 0:
        raise ValueError(f"LAPLACE_PRIOR_C must be >= 0, got {v!r}")
    return v


class Config:
    SECRET_KEY   = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV    = os.getenv("FLASK_ENV", "development")
    DEBUG        = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    PORT         = int(os.getenv("PORT", 5004))
    SERVICE_NAME = "metric-processor"
    VERSION      = "1.0.0"

    # Base de datos
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = int(os.getenv("DB_PORT", 5432))
    DB_NAME     = os.getenv("DB_NAME", "olh_sentiment")
    DB_USER     = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_SSLMODE  = os.getenv("DB_SSLMODE", "require")

    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", 1))
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", 10))

    # Suavizado bayesiano del score (positivo vs no positivo): (pos + C·m) / (N + C) × 100
    LAPLACE_PRIOR_M = _parse_laplace_prior_m()
    LAPLACE_PRIOR_C = _parse_laplace_prior_c()
