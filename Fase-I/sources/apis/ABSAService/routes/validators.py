"""
Funciones de validación reutilizables para los endpoints del servicio ABSA.
"""

_REGLAS_PROCESAR = [
    {
        "campo":   "archivo_id",
        "regla":   lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
        "mensaje": "archivo_id debe ser un entero mayor a 0",
    },
]


def validar_body_procesar(body: dict) -> list[str]:
    """
    Valida los campos requeridos del body para POST /procesar.

    Retorna una lista de mensajes de error.
    Si la lista está vacía, el body es válido.
    """
    if not isinstance(body, dict) or not body:
        return ["El body de la petición no puede estar vacío"]

    errores = []
    for regla in _REGLAS_PROCESAR:
        campo = regla["campo"]
        if campo not in body:
            errores.append(f"El campo '{campo}' es requerido")
            continue
        if not regla["regla"](body[campo]):
            errores.append(regla["mensaje"])

    return errores


_REGLAS_SINCRONIZAR_BATCH = [
    {
        "campo":   "openai_batch_id",
        "regla":   lambda v: v is None or (isinstance(v, str) and len(v.strip()) > 0),
        "mensaje": "openai_batch_id debe ser una cadena no vacía u omitirse",
    },
]


def validar_body_sincronizar_batch(body: dict | None) -> list[str]:
    """Valida POST /batch/sincronizar (body opcional con openai_batch_id)."""
    if body is None or body == {}:
        return []

    if not isinstance(body, dict):
        return ["El body de la petición debe ser un objeto JSON"]

    errores = []
    if "openai_batch_id" in body:
        for regla in _REGLAS_SINCRONIZAR_BATCH:
            campo = regla["campo"]
            if campo not in body:
                continue
            if not regla["regla"](body[campo]):
                errores.append(regla["mensaje"])
    return errores
