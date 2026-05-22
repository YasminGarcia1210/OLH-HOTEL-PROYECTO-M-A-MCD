# metricas-read

Librería compartida para consultar métricas pre-calculadas en PostgreSQL.

El proceso anfitrión (p. ej. DashboardBackend) debe inicializar el pool y exponer el módulo top-level `db` compatible con `get_connection()` antes de llamar a estas funciones.
