"""
Modelo ABSA basado en LLM.

Reintenta hasta MAX_REINTENTOS veces si el JSON es inválido.

El LLM retorna una lista plana {"items": [...]}.  Cada ítem con slug que
coincida con un tópico predefinido se trata como tópico fijo; el resto
como tópico dinámico.
"""

import logging
import json
import re
from dataclasses import dataclass, field

from lib.prompt_builder import construir_prompt
from services.exceptions import LLMError, RespuestaLLMInvalidaError
from services.llm.base import BaseLLM

logger = logging.getLogger(__name__)

MAX_REINTENTOS = 2

_SENTIMIENTOS = {"positivo", "negativo", "neutro"}


@dataclass
class TopicoFijoResultado:
    slug:         str
    mencionado:   bool
    sentimiento:  str | None
    score_topico: float | None
    fragmento:    str | None


@dataclass
class TopicoDinamicoResultado:
    nombre:       str
    sentimiento:  str
    score_topico: float
    fragmento:    str
    slug:         str = ""  # slug del tópico existente si se reutiliza uno; vacío si es nuevo


@dataclass
class ABSAResultado:
    topicos_fijos:     list[TopicoFijoResultado]     = field(default_factory=list)
    topicos_dinamicos: list[TopicoDinamicoResultado] = field(default_factory=list)
    tokens_entrada:    int = 0
    tokens_salida:     int = 0


class ABSALLMModel:

    def __init__(self, llm: BaseLLM):
        self._llm = llm

    @property
    def version(self) -> str:
        return self._llm.version

    def analizar(
        self,
        texto: str,
        topicos_fijos: list[dict],
        topicos_adicionales: list[dict] | None = None,
    ) -> ABSAResultado:
        """
        Analiza una review y retorna los tópicos mencionados con su sentimiento.

        Args:
            texto:               Texto limpio de la review.
            topicos_fijos:       Lista de dicts con 'id', 'slug' y 'nombre'.
            topicos_adicionales: Tópicos adicionales ya existentes en BD (opcional).

        Returns:
            ABSAResultado con listas de tópicos fijos y dinámicos.

        Lanza:
            RespuestaLLMInvalidaError si tras MAX_REINTENTOS el JSON sigue inválido.
            LLMError / subclases para fallos de conexión o autenticación.
        """
        prompt = construir_prompt(texto, topicos_fijos, topicos_adicionales)
        slugs_esperados = {t["slug"] for t in topicos_fijos}

        ultimo_error = None
        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                respuesta = self._llm.completar(prompt)
                resultado = _parsear_respuesta(respuesta.texto, slugs_esperados)
                resultado.tokens_entrada = respuesta.tokens_entrada
                resultado.tokens_salida  = respuesta.tokens_salida
                return resultado
            except RespuestaLLMInvalidaError as e:
                ultimo_error = e
                logger.warning("Intento %d/%d — JSON inválido: %s", intento, MAX_REINTENTOS, e)
            except LLMError:
                raise

        raise RespuestaLLMInvalidaError(
            f"El LLM no retornó JSON válido tras {MAX_REINTENTOS} intentos. "
            f"Último error: {ultimo_error}"
        )


# ── Helpers de parseo ─────────────────────────────────────────────────────────

def _parsear_respuesta(raw: str, slugs_esperados: set[str]) -> ABSAResultado:
    """Parsea la respuesta cruda del LLM al dataclass ABSAResultado."""
    texto_json = _extraer_json(raw)

    try:
        data = json.loads(texto_json)
    except json.JSONDecodeError as e:
        raise RespuestaLLMInvalidaError(f"No es JSON válido: {e}. Respuesta: {raw[:300]}") from e

    if not isinstance(data, dict):
        raise RespuestaLLMInvalidaError(f"Se esperaba un objeto JSON, se obtuvo: {type(data)}")

    items = data.get("items", [])
    if not isinstance(items, list):
        raise RespuestaLLMInvalidaError(f"El campo 'items' debe ser una lista, se obtuvo: {type(items)}")

    topicos_fijos: list[TopicoFijoResultado] = []
    topicos_dinamicos: list[TopicoDinamicoResultado] = []
    slugs_mencionados: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        slug        = str(item.get("slug") or "").strip()
        nombre      = str(item.get("topico") or "").strip()
        fragmento   = str(item.get("fragmento") or "").strip()[:500]
        sentimiento = str(item.get("sentimiento_topico") or "neutro").lower()
        if sentimiento not in _SENTIMIENTOS:
            sentimiento = "neutro"

        raw_score = item.get("score_topico")
        score = float(raw_score) if raw_score is not None else 0.5
        score = max(0.0, min(1.0, score))

        if slug in slugs_esperados:
            slugs_mencionados.add(slug)
            topicos_fijos.append(TopicoFijoResultado(
                slug=slug,
                mencionado=True,
                sentimiento=sentimiento,
                score_topico=score,
                fragmento=fragmento or None,
            ))
        else:
            if not nombre:
                continue
            topicos_dinamicos.append(TopicoDinamicoResultado(
                nombre=nombre[:120],
                sentimiento=sentimiento,
                score_topico=score,
                fragmento=fragmento,
                slug=slug,  # preserva slug cuando el LLM reutiliza un tópico adicional existente
            ))

    # Agregar tópicos fijos no mencionados para mantener consistencia
    for slug in slugs_esperados:
        if slug not in slugs_mencionados:
            topicos_fijos.append(TopicoFijoResultado(
                slug=slug,
                mencionado=False,
                sentimiento=None,
                score_topico=None,
                fragmento=None,
            ))

    return ABSAResultado(topicos_fijos=topicos_fijos, topicos_dinamicos=topicos_dinamicos)


def _extraer_json(raw: str) -> str:
    """
    Extrae el bloque JSON de la respuesta aunque el LLM haya
    añadido texto antes/después o marcadores ```json ... ```.
    """
    sin_md = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    inicio = sin_md.find("{")
    fin    = sin_md.rfind("}")
    if inicio == -1 or fin == -1 or fin < inicio:
        raise RespuestaLLMInvalidaError(f"No se encontró objeto JSON en la respuesta: {raw[:300]}")
    return sin_md[inicio:fin + 1]
