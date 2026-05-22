"""
Validadores de query params para los endpoints de metricas.

Cada función devuelve una lista de mensajes de error; lista vacía = válido.
"""

import datetime
import re

_RE_YYYY_MM = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
_RE_SLUG_TOPICO = re.compile(r"^[a-z0-9_]+$")

SENTIMIENTOS_VALIDOS = {"positivo", "negativo", "neutro"}
ORDENES_VALIDOS = {"fecha_desc", "fecha_asc"}

# Tope máximo para GET /metricas/archivos/entrada?limite=
LIMITE_LISTADO_BLOBS_MAX = 5000


def validar_dashboard_reviews_args(args) -> list[str]:
    """
    Valida los query params de GET /api/v1/metricas/reviews.

    Parámetros esperados en `args` (flask.request.args):
      hotel_id, fecha_desde, fecha_hasta, sentimiento,
      topico_slug, topico_id, page, page_size, orden
    """
    errores: list[str] = []

    # hotel_id: obligatorio, entero positivo
    hotel_id_raw = args.get("hotel_id")
    if hotel_id_raw is None:
        errores.append("hotel_id es obligatorio.")
    else:
        try:
            hotel_id = int(hotel_id_raw)
            if hotel_id < 1:
                errores.append("hotel_id debe ser un entero positivo.")
        except (ValueError, TypeError):
            errores.append("hotel_id debe ser un entero positivo.")

    # fechas: opcionales pero deben ser ISO-8601 si se proveen
    fecha_desde = None
    fecha_hasta = None

    fecha_desde_raw = args.get("fecha_desde")
    if fecha_desde_raw is not None:
        try:
            fecha_desde = datetime.date.fromisoformat(fecha_desde_raw)
        except ValueError:
            errores.append("fecha_desde debe tener formato ISO-8601 (YYYY-MM-DD).")

    fecha_hasta_raw = args.get("fecha_hasta")
    if fecha_hasta_raw is not None:
        try:
            fecha_hasta = datetime.date.fromisoformat(fecha_hasta_raw)
        except ValueError:
            errores.append("fecha_hasta debe tener formato ISO-8601 (YYYY-MM-DD).")

    if fecha_desde is not None and fecha_hasta is not None:
        if fecha_desde > fecha_hasta:
            errores.append("fecha_desde no puede ser posterior a fecha_hasta.")

    # sentimiento: opcional, debe ser uno de los valores permitidos
    sentimiento = args.get("sentimiento")
    if sentimiento is not None and sentimiento not in SENTIMIENTOS_VALIDOS:
        errores.append(
            f"sentimiento debe ser uno de: {', '.join(sorted(SENTIMIENTOS_VALIDOS))}."
        )

    # topico_id: si se provee sin topico_slug, debe ser entero positivo
    topico_slug = args.get("topico_slug")
    topico_id_raw = args.get("topico_id")
    if topico_slug is None and topico_id_raw is not None:
        try:
            topico_id = int(topico_id_raw)
            if topico_id < 1:
                errores.append("topico_id debe ser un entero positivo.")
        except (ValueError, TypeError):
            errores.append("topico_id debe ser un entero positivo.")

    # page: opcional, entero ≥ 1
    page_raw = args.get("page")
    if page_raw is not None:
        try:
            page = int(page_raw)
            if page < 1:
                errores.append("page debe ser un entero mayor o igual a 1.")
        except (ValueError, TypeError):
            errores.append("page debe ser un entero mayor o igual a 1.")

    # page_size: opcional, 1–100
    page_size_raw = args.get("page_size")
    if page_size_raw is not None:
        try:
            page_size = int(page_size_raw)
            if not (1 <= page_size <= 100):
                errores.append("page_size debe estar entre 1 y 100.")
        except (ValueError, TypeError):
            errores.append("page_size debe ser un entero entre 1 y 100.")

    # orden: opcional, valor controlado
    orden = args.get("orden")
    if orden is not None and orden not in ORDENES_VALIDOS:
        errores.append(
            f"orden debe ser uno de: {', '.join(sorted(ORDENES_VALIDOS))}."
        )

    return errores


def validar_query_sentimiento_mensual(args: dict) -> list[str]:
    """
    Valida los query params de GET /sentimiento-mensual.

    Reglas:
    - hotel_id: requerido, entero positivo.
    - Modo rango (desde + hasta): ambos en YYYY-MM, desde <= hasta.
    - Modo meses: entero entre 1 y 24.
    - Si no se pasa ni meses ni desde/hasta, se usa el default (12 meses) y es válido.
    - desde y hasta son mutuamente dependientes: deben ir juntos.
    """
    errores: list[str] = []

    hotel_id_raw = args.get("hotel_id")
    if hotel_id_raw is None:
        errores.append("El parámetro 'hotel_id' es requerido")
    else:
        try:
            if int(hotel_id_raw) <= 0:
                errores.append("'hotel_id' debe ser un entero mayor a 0")
        except (ValueError, TypeError):
            errores.append("'hotel_id' debe ser un entero")

    desde = args.get("desde")
    hasta = args.get("hasta")
    meses_raw = args.get("meses")

    usar_rango = desde is not None or hasta is not None

    if usar_rango:
        if desde is None:
            errores.append("El parámetro 'desde' es requerido cuando se especifica 'hasta'")
        elif not _RE_YYYY_MM.match(desde):
            errores.append("'desde' debe tener formato YYYY-MM (ej: 2025-01)")

        if hasta is None:
            errores.append("El parámetro 'hasta' es requerido cuando se especifica 'desde'")
        elif not _RE_YYYY_MM.match(hasta):
            errores.append("'hasta' debe tener formato YYYY-MM (ej: 2025-11)")

        if desde and hasta and _RE_YYYY_MM.match(desde) and _RE_YYYY_MM.match(hasta):
            if desde > hasta:
                errores.append("'desde' no puede ser posterior a 'hasta'")
    elif meses_raw is not None:
        try:
            meses = int(meses_raw)
            if not (1 <= meses <= 24):
                errores.append("'meses' debe estar entre 1 y 24")
        except (ValueError, TypeError):
            errores.append("'meses' debe ser un entero")

    return errores


def validar_query_topicos_mensual(args) -> list[str]:
    """
    Valida los query params de GET /topicos (métricas por tópico del mes).

    Requeridos: hotel_id, anio, mes.
    Opcionales: tipo ∈ {clave, adicional}, solo_alertas booleano.
    """
    errores: list[str] = []

    hotel_id_raw = args.get("hotel_id")
    if hotel_id_raw is None:
        errores.append("El parámetro 'hotel_id' es requerido")
    else:
        try:
            if int(hotel_id_raw) <= 0:
                errores.append("'hotel_id' debe ser un entero mayor a 0")
        except (ValueError, TypeError):
            errores.append("'hotel_id' debe ser un entero")

    anio_raw = args.get("anio")
    if anio_raw is None:
        errores.append("El parámetro 'anio' es requerido")
    else:
        try:
            anio = int(anio_raw)
            if not (1 <= anio <= 9999):
                errores.append("'anio' debe estar entre 1 y 9999")
        except (ValueError, TypeError):
            errores.append("'anio' debe ser un entero")

    mes_raw = args.get("mes")
    if mes_raw is None:
        errores.append("El parámetro 'mes' es requerido")
    else:
        try:
            mes = int(mes_raw)
            if not (1 <= mes <= 12):
                errores.append("'mes' debe estar entre 1 y 12")
        except (ValueError, TypeError):
            errores.append("'mes' debe ser un entero")

    tipo = args.get("tipo")
    if tipo is not None and str(tipo).strip() != "":
        if tipo not in ("clave", "adicional"):
            errores.append("'tipo' debe ser 'clave' o 'adicional'")

    solo = args.get("solo_alertas")
    if solo is not None and str(solo).strip() != "":
        if str(solo).lower() not in ("true", "false", "1", "0", "yes", "no"):
            errores.append("'solo_alertas' debe ser true o false")

    return errores


def validar_query_kpis_mensual(args) -> list[str]:
    """
    Valida los query params de GET /kpis (lectura mensual agregada).

    Requeridos: hotel_id, anio, mes.
    Reglas:
    - hotel_id: entero mayor a 0.
    - anio: entero mayor o igual a 2020.
    - mes: entero entre 1 y 12.
    """
    errores: list[str] = []

    hotel_id_raw = args.get("hotel_id")
    if hotel_id_raw is None:
        errores.append("El parámetro 'hotel_id' es requerido")
    else:
        try:
            if int(hotel_id_raw) <= 0:
                errores.append("'hotel_id' debe ser un entero mayor a 0")
        except (ValueError, TypeError):
            errores.append("'hotel_id' debe ser un entero")

    anio_raw = args.get("anio")
    if anio_raw is None:
        errores.append("El parámetro 'anio' es requerido")
    else:
        try:
            if int(anio_raw) < 2020:
                errores.append("'anio' debe ser un entero mayor o igual a 2020")
        except (ValueError, TypeError):
            errores.append("'anio' debe ser un entero")

    mes_raw = args.get("mes")
    if mes_raw is None:
        errores.append("El parámetro 'mes' es requerido")
    else:
        try:
            mes = int(mes_raw)
            if not (1 <= mes <= 12):
                errores.append("'mes' debe estar entre 1 y 12")
        except (ValueError, TypeError):
            errores.append("'mes' debe ser un entero")

    return errores


def validar_query_alertas(args) -> list[str]:
    """
    Valida los query params de GET /alertas.

    Requeridos: hotel_id.
    Opcionales: resuelta booleano.
    """
    errores: list[str] = []

    hotel_id_raw = args.get("hotel_id")
    if hotel_id_raw is None:
        errores.append("El parámetro 'hotel_id' es requerido")
    else:
        try:
            if int(hotel_id_raw) <= 0:
                errores.append("'hotel_id' debe ser un entero mayor a 0")
        except (ValueError, TypeError):
            errores.append("'hotel_id' debe ser un entero")

    resuelta_raw = args.get("resuelta")
    if resuelta_raw is not None and str(resuelta_raw).strip() != "":
        if str(resuelta_raw).lower() not in ("true", "false", "1", "0", "yes", "no"):
            errores.append("'resuelta' debe ser true o false")

    return errores


def validar_slug_topico(slug: str | None) -> list[str]:
    """
    Valida el path param `slug` de endpoints de tópico detalle.
    """
    if slug is None:
        return ["El parámetro de ruta 'slug' es requerido"]

    slug_norm = str(slug).strip()
    if slug_norm == "":
        return ["El parámetro de ruta 'slug' no puede estar vacío"]
    if not _RE_SLUG_TOPICO.match(slug_norm):
        return ["'slug' solo permite letras minúsculas, números y guion bajo"]

    return []


def validar_query_archivos_entrada(args) -> list[str]:
    """
    Valida query params de GET /api/v1/metricas/archivos/entrada.

    Opcional:
      limite (entero 1..LIMITE_LISTADO_BLOBS_MAX) — tope al listar blobs en Azure.
      pipeline_page, pipeline_page_size — paginación de filas en log_archivos (1..100).
      pendientes_page, pendientes_page_size — paginación de blobs pendientes (1..100).
    """
    errores: list[str] = []
    limite_raw = args.get("limite")
    if limite_raw is not None and str(limite_raw).strip() != "":
        try:
            limite = int(limite_raw)
            if limite < 1:
                errores.append("'limite' debe ser un entero mayor o igual a 1.")
            elif limite > LIMITE_LISTADO_BLOBS_MAX:
                errores.append(
                    f"'limite' no puede superar {LIMITE_LISTADO_BLOBS_MAX}."
                )
        except (ValueError, TypeError):
            errores.append("'limite' debe ser un entero.")

    for key in ("pipeline_page", "pendientes_page"):
        raw = args.get(key)
        if raw is not None and str(raw).strip() != "":
            try:
                n = int(raw)
                if n < 1:
                    errores.append(f"'{key}' debe ser un entero mayor o igual a 1.")
            except (ValueError, TypeError):
                errores.append(f"'{key}' debe ser un entero mayor o igual a 1.")

    for key in ("pipeline_page_size", "pendientes_page_size"):
        raw = args.get(key)
        if raw is not None and str(raw).strip() != "":
            try:
                n = int(raw)
                if not (1 <= n <= 100):
                    errores.append(f"'{key}' debe estar entre 1 y 100.")
            except (ValueError, TypeError):
                errores.append(f"'{key}' debe ser un entero entre 1 y 100.")

    return errores


def validar_body_recalcular_semestre(body: dict) -> list[str]:
    """
    Valida el body de POST /api/v1/metricas/recalcular-semestre.

    Requiere: hotel_id (int > 0).
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

    return errores


def validar_upload_archivo(file_storage) -> list[str]:
    """
    Valida el archivo multipart del campo `archivo` (POST /metricas/archivos/upload).
    """
    errores: list[str] = []
    if file_storage is None:
        errores.append("El campo 'archivo' es obligatorio.")
        return errores
    fn = getattr(file_storage, "filename", None)
    if fn is None or str(fn).strip() == "":
        errores.append("El archivo debe tener un nombre.")
    return errores
