"""
Funciones de validación reutilizables para los endpoints del servicio.
"""


ESTADOS_VALIDOS = {"received", "validated", "cleaned", "predicted", "topics_identified", "completed", "error"}

# Campos requeridos por endpoint, con tipo esperado y reglas adicionales
_REGLAS_EJECUTAR = [
    {
        "campo":  "hotel_id",
        "tipo":   int,
        "regla":  lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
        "mensaje": "hotel_id debe ser un entero mayor a 0"
    },
    {
        "campo":  "drive_id_origen",
        "tipo":   str,
        "regla":  lambda v: isinstance(v, str) and len(v.strip()) > 0,
        "mensaje": "drive_id_origen debe ser la ruta del blob en el contenedor Azure (no vacía)",
    },
    {
        "campo":  "nombre_archivo_origen",
        "tipo":   str,
        "regla":  lambda v: isinstance(v, str) and v.strip().lower().endswith(".csv"),
        "mensaje": "nombre_archivo_origen debe ser un nombre de archivo .csv"
    },
    {
        "campo":  "plataforma",
        "tipo":   str,
        "regla":  lambda v: (
            isinstance(v, str)
            and 0 < len(v.strip()) <= 60
        ),
        "mensaje": "plataforma debe ser un texto no vacío de como máximo 60 caracteres",
    },
]


def validar_body_ejecutar(body: dict) -> list[str]:
    """
    Valida los campos requeridos del body para POST /ejecutar
    (hotel_id, drive_id_origen como ruta de blob Azure, nombre_archivo_origen, plataforma).

    Retorna una lista de mensajes de error.
    Si la lista está vacía, el body es válido.
    """
    errores = []

    if not isinstance(body, dict) or not body:
        return ["El body de la petición no puede estar vacío"]

    for regla in _REGLAS_EJECUTAR:
        campo = regla["campo"]

        if campo not in body:
            errores.append(f"El campo '{campo}' es requerido")
            continue

        if not regla["regla"](body[campo]):
            errores.append(regla["mensaje"])

    return errores
