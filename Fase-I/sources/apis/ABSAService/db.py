"""
Gestión del pool de conexiones a PostgreSQL (Neon).

Usa psycopg2.pool.ThreadedConnectionPool para garantizar conexiones
persistentes y thread-safe. Una conexión se toma del pool al iniciar
una operación y se devuelve automáticamente al terminar, tanto en caso
de éxito como de error.

Uso desde cualquier módulo:
    from db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
"""

import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_pool: pg_pool.ThreadedConnectionPool | None = None

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
    Inicializa el pool de conexiones con la configuración de la app.
    Debe llamarse una sola vez al arrancar la aplicación (en create_app).
    """
    global _pool

    if _pool is not None:
        logger.warning("El pool de conexiones ya estaba inicializado.")
        return

    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL no está configurada. Revisa el archivo .env.")

    _pool = pg_pool.ThreadedConnectionPool(
        minconn=config.DB_POOL_MIN,
        maxconn=config.DB_POOL_MAX,
        dsn=config.DATABASE_URL,
    )

    logger.info(
        "Pool de conexiones inicializado desde DATABASE_URL (min=%s, max=%s)",
        config.DB_POOL_MIN, config.DB_POOL_MAX,
    )


def close_pool() -> None:
    """
    Cierra todas las conexiones del pool.
    Debe llamarse al detener la aplicación.
    """
    global _pool

    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("Pool de conexiones cerrado.")


@contextmanager
def get_connection():
    """
    Context manager que entrega una conexión del pool y la devuelve
    automáticamente al terminar, sin importar si hubo error.

    Hace commit automático si no hubo excepciones; rollback si las hubo.
    Antes del yield se valida la conexión (SELECT 1 + rollback).

    Ejemplo:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM reviews WHERE id = %s", (1,))
                row = cur.fetchone()
    """
    if _pool is None:
        raise RuntimeError("El pool de conexiones no está inicializado. Llama a init_pool() primero.")

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
