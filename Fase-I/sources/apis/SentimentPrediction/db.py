"""
Pool de conexiones PostgreSQL (mismo patrón que DataVerificationCleanner).

El pool se crea de forma perezosa en la primera operación que necesita BD,
para que `create_app()` pueda arrancar aunque PostgreSQL no esté disponible
(p. ej. solo comprobar GET /health).
"""

import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_pool: pg_pool.ThreadedConnectionPool | None = None
_config = None

_CHECKOUT_ATTEMPTS = 3


def _acquire_live_connection(pool: pg_pool.ThreadedConnectionPool):
    """
    Obtiene una conexión del pool tras comprobarla con SELECT 1 y rollback
    inmediato. Conexiones rotas se descartan con putconn(..., close=True)
    (API psycopg2 2.9 ThreadedConnectionPool).
    """
    last_exc: BaseException | None = None
    for attempt in range(1, _CHECKOUT_ATTEMPTS + 1):
        conn = None
        try:
            conn = pool.getconn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            try:
                conn.rollback()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
                logger.warning(
                    "Rollback tras ping falló (intento %s/%s), descartando: %s",
                    attempt,
                    _CHECKOUT_ATTEMPTS,
                    exc,
                )
                pool.putconn(conn, close=True)
                conn = None
                last_exc = exc
                continue
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            last_exc = exc
            logger.warning(
                "Ping de conexión del pool falló (intento %s/%s): %s",
                attempt,
                _CHECKOUT_ATTEMPTS,
                exc,
            )
            if conn is not None:
                pool.putconn(conn, close=True)
            conn = None
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("No se obtuvo conexión viva del pool")


def init_pool(config) -> None:
    """
    Registra la configuración para abrir el pool en la primera conexión.
    """
    global _config
    _config = config
    logger.info(
        "Configuración de BD registrada para %s:%s/%s",
        config.DB_HOST,
        config.DB_PORT,
        config.DB_NAME,
    )


def _ensure_pool() -> None:
    global _pool, _config

    if _pool is not None:
        return
    if _config is None:
        raise RuntimeError("init_pool() no fue llamado.")

    _pool = pg_pool.ThreadedConnectionPool(
        minconn=_config.DB_POOL_MIN,
        maxconn=_config.DB_POOL_MAX,
        host=_config.DB_HOST,
        port=_config.DB_PORT,
        dbname=_config.DB_NAME,
        user=_config.DB_USER,
        password=_config.DB_PASSWORD,
        sslmode=_config.DB_SSLMODE,
    )

    logger.info(
        "Pool de conexiones inicializado: %s:%s/%s (min=%s, max=%s)",
        _config.DB_HOST,
        _config.DB_PORT,
        _config.DB_NAME,
        _config.DB_POOL_MIN,
        _config.DB_POOL_MAX,
    )


def close_pool() -> None:
    global _pool

    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("Pool de conexiones cerrado.")


@contextmanager
def get_connection():
    _ensure_pool()
    if _pool is None:
        raise RuntimeError("El pool de conexiones no está disponible.")

    conn = None
    try:
        conn = _acquire_live_connection(_pool)
        try:
            yield conn
            conn.commit()
        except psycopg2.Error as db_err:
            if not conn.closed:
                try:
                    conn.rollback()
                except psycopg2.Error:
                    pass
            logger.error("Error de base de datos: %s", db_err)
            raise
        except Exception as err:
            if not conn.closed:
                try:
                    conn.rollback()
                except psycopg2.Error:
                    pass
            logger.error("Error inesperado durante operación de BD: %s", err)
            raise
    finally:
        if conn is not None:
            if conn.closed:
                _pool.putconn(conn, close=True)
            else:
                _pool.putconn(conn)
