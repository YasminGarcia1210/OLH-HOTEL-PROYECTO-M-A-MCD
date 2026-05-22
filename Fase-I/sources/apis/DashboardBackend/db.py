"""
Pool de conexiones a PostgreSQL para DashboardBackend.

Uso desde cualquier módulo:
    from db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
"""

import logging
import threading
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_pool: pg_pool.ThreadedConnectionPool | None = None
_pool_config = None
_pool_lock = threading.Lock()

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
    Registra la configuración del pool. La conexión real a PostgreSQL se abre de
    forma diferida en el primer ``get_connection()`` (lazy), para que el proceso
    pueda arrancar (p. ej. ``GET /health`` en Container Apps) aunque la BD tarde
    o falle el firewall; las rutas que usan BD fallarán hasta que la conexión sea válida.
    """
    global _pool_config

    if _pool is not None:
        logger.warning("El pool de conexiones ya estaba inicializado.")
        return

    _pool_config = config
    logger.info(
        "Pool configurado (lazy): %s:%s/%s (min=%s, max=%s) — conexión al primer uso",
        config.DB_HOST, config.DB_PORT, config.DB_NAME,
        config.DB_POOL_MIN, config.DB_POOL_MAX,
    )


def _ensure_pool() -> None:
    global _pool

    if _pool is not None:
        return
    if _pool_config is None:
        raise RuntimeError("El pool de conexiones no está inicializado. Llama a init_pool() primero.")

    with _pool_lock:
        if _pool is not None:
            return
        cfg = _pool_config
        _pool = pg_pool.ThreadedConnectionPool(
            minconn=cfg.DB_POOL_MIN,
            maxconn=cfg.DB_POOL_MAX,
            host=cfg.DB_HOST,
            port=cfg.DB_PORT,
            dbname=cfg.DB_NAME,
            user=cfg.DB_USER,
            password=cfg.DB_PASSWORD,
            sslmode=cfg.DB_SSLMODE,
        )
        logger.info(
            "Pool de conexiones creado: %s:%s/%s",
            cfg.DB_HOST, cfg.DB_PORT, cfg.DB_NAME,
        )


def close_pool() -> None:
    global _pool, _pool_config

    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("Pool de conexiones cerrado.")
    _pool_config = None


@contextmanager
def get_connection():
    """
    Context manager que entrega una conexión del pool con RealDictCursor
    habilitado por defecto, y la devuelve automáticamente al terminar.
    Hace commit si no hubo excepción; rollback si la hubo.
    Antes del yield se valida la conexión (SELECT 1 + rollback).
    """
    _ensure_pool()

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
