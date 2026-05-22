"""
Funciones de validación para POST /api/v1/metricas/calcular y POST /api/v1/metricas/recalcular.

Las consultas de métricas (GET) viven en DashboardBackend; sus validadores están
en `sources/apis/DashboardBackend/routes/validators.py`.
"""


def validar_body_calcular(body: dict) -> list[str]:
    """
    Valida los campos requeridos del body para POST /calcular.

    Retorna una lista de mensajes de error.
    Si la lista está vacía, el body es válido.
    """
    if not isinstance(body, dict) or not body:
        return ["El body de la petición no puede estar vacío"]

    errores = []

    if "archivo_id" not in body:
        errores.append("El campo 'archivo_id' es requerido")
    elif not isinstance(body["archivo_id"], int) or isinstance(body["archivo_id"], bool) or body["archivo_id"] <= 0:
        errores.append("archivo_id debe ser un entero mayor a 0")

    return errores


def validar_body_recalcular(body: dict) -> list[str]:
    """
    Valida el body de POST /api/v1/metricas/recalcular.

    Requiere: hotel_id (int > 0), anio (int >= 2000), mes (int 1-12).
    """
    if not isinstance(body, dict) or not body:
        return ["El body de la petición no puede estar vacío"]

    errores: list[str] = []

    if "hotel_id" not in body:
        errores.append("El campo 'hotel_id' es requerido")
    elif (
        not isinstance(body["hotel_id"], int)
        or isinstance(body["hotel_id"], bool)
        or body["hotel_id"] <= 0
    ):
        errores.append("hotel_id debe ser un entero mayor a 0")

    if "anio" not in body:
        errores.append("El campo 'anio' es requerido")
    elif not isinstance(body["anio"], int) or isinstance(body["anio"], bool):
        errores.append("anio debe ser un entero")
    elif body["anio"] < 2000:
        errores.append("anio debe ser >= 2000")

    if "mes" not in body:
        errores.append("El campo 'mes' es requerido")
    elif not isinstance(body["mes"], int) or isinstance(body["mes"], bool):
        errores.append("mes debe ser un entero")
    elif not 1 <= body["mes"] <= 12:
        errores.append("mes debe estar entre 1 y 12")

    return errores
