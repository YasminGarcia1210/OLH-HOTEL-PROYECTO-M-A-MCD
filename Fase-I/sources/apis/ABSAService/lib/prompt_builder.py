"""
Construcción del prompt para el análisis ABSA con LLM.

El prompt retorna una lista plana de ítems; cada ítem incluye tópico,
slug, fragmento, sentimiento_topico y score_topico.  Los tópicos predefinidos
llevan el slug exacto; los dinámicos usan un nombre libre (sin slug).
"""

_PLANTILLA = """\
Eres un analista de opiniones de hoteles. Lee la review en español e identifica TODOS los tópicos (aspectos) reales que menciona el cliente.

Tópicos predefinidos (usa nombre y slug EXACTOS):
{topicos}
{seccion_adicionales}

Objetivo:
- Extraer cada aspecto concreto que mencione la review (servicio, instalaciones, ubicación, ruido, vista, parking, wifi, piscina, etc.).
- Reutilizar un tópico existente cuando el aspecto encaje semánticamente con él.
- Crear un tópico nuevo cuando el aspecto NO tenga relación semántica con ningún tópico existente.

Procedimiento (en este orden, por cada aspecto detectado):
1) ¿Encaja semánticamente en un tópico predefinido (es el mismo concepto o un subtema claro)? → úsalo con su slug EXACTO.
2) ¿Encaja semánticamente en un tópico adicional ya descubierto? → reutilízalo con su slug EXACTO.
3) Si no hay relación semántica razonable con ninguno → crea un tópico nuevo con slug="" y un nombre breve, descriptivo y en minúsculas (p. ej. "ubicación", "ruido", "wifi", "piscina", "parking", "vista", "check-in").

Encaje semántico = mismo concepto, sinónimo o subtema directo. NO fuerces aspectos que tratan cosas distintas dentro del mismo tópico solo por cercanía temática amplia.

Guía de mapeo (subtemas que SÍ caen en cada predefinido):
- instalaciones_servicios: mantenimiento, estado del hotel/habitación/baño, agua caliente, ducha, ascensor, climatización, averías, sanitarios.
- atencion_cliente: recepción, trato del personal, amabilidad, tiempos de respuesta, gestión de quejas.
- desayuno_gastronomia: desayuno, comida, bebidas, restaurante, calidad de alimentos.
- comodidad: cama, colchón, almohadas, descanso, temperatura para dormir.
- limpieza: higiene, suciedad, olores, aseo de habitación o áreas comunes.
- calidad_precio: precio, costo-beneficio, valor percibido frente a lo recibido.

Aspectos que normalmente NO encajan en los predefinidos y suelen ser tópicos nuevos si aparecen:
- ubicación / zona / cercanía a atracciones
- ruido / aislamiento acústico
- wifi / conexión a internet
- parking / estacionamiento
- piscina, gimnasio, spa (si la review los trata como aspecto propio)
- vista / habitación con vista
- check-in / check-out / reserva
- seguridad

Extracción:
- Una review puede tener varios tópicos; extrae todos los que se mencionen.
- Usa fragmentos literales del texto (20 a 300 caracteres) que justifiquen cada tópico.
- sentimiento_topico: "positivo" o "negativo" según el fragmento.
- score_topico: 0.000 a 1.000 (confianza en la asignación).
- No dupliques ítems semánticamente equivalentes; agrúpalos en un solo ítem.

Uso de "General" (excepcional):
- Solo cuando la review NO contiene ningún aspecto concreto: saludos, agradecimientos vagos, frases tipo "todo bien", "muy mal" sin detalle, o texto irrelevante.
- En ese caso, devuelve UN solo ítem con topico="General", slug="general", el fragmento más representativo, sentimiento según el tono y score_topico=1.000.
- NUNCA uses "General" si la review menciona al menos un aspecto identificable.

Responde SOLO JSON válido.

TEXTO DE LA REVIEW:
{texto}

Formato obligatorio:
{{"items":[{{"topico":"...","slug":"...","fragmento":"...","sentimiento_topico":"positivo|negativo","score_topico":0.000}}]}}"""

_SECCION_ADICIONALES = """\
Tópicos adicionales ya descubiertos (si la review menciona algo equivalente, \
REUTILIZA uno de estos con su slug EXACTO en lugar de crear uno nuevo):
{adicionales}
"""


def construir_prompt(
    texto: str,
    topicos_fijos: list[dict],
    topicos_adicionales: list[dict] | None = None,
) -> str:
    lineas_fijos = [f"- {t['nombre']} (slug: {t['slug']})" for t in topicos_fijos]

    if topicos_adicionales:
        lineas_ad = [f"- {t['nombre']} (slug: {t['slug']})" for t in topicos_adicionales]
        seccion = _SECCION_ADICIONALES.format(adicionales="\n".join(lineas_ad))
    else:
        seccion = ""

    return _PLANTILLA.format(
        topicos="\n".join(lineas_fijos),
        seccion_adicionales=seccion,
        texto=texto.strip(),
    )
