"""
Proveedor LLM: Google Gemini.

Usa el SDK unificado google-genai (>= 1.0).

Requiere:
    GEMINI_API_KEY — clave de API de Google AI Studio.
    GEMINI_MODEL   — modelo a usar (default: gemini-3.1-flash-lite).
"""

import logging

from services.exceptions import LLMAutenticacionError, LLMConexionError, LLMError
from services.llm.base import BaseLLM, LLMRespuesta

logger = logging.getLogger(__name__)


class GeminiLLM(BaseLLM):

    def __init__(self, config):
        try:
            from google import genai
            from google.genai import errors as genai_errors
            self._genai_errors = genai_errors
            self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        except ImportError as e:
            raise LLMError("El paquete 'google-genai' no está instalado.") from e

        self._model_name = config.GEMINI_MODEL

    @property
    def version(self) -> str:
        return f"llm-gemini-{self._model_name}"

    def completar(self, prompt: str) -> LLMRespuesta:
        try:
            respuesta = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )
            meta = respuesta.usage_metadata
            return LLMRespuesta(
                texto=respuesta.text or "",
                tokens_entrada=meta.prompt_token_count if meta else 0,
                tokens_salida=meta.candidates_token_count if meta else 0,
            )
        except self._genai_errors.ClientError as e:
            raise LLMAutenticacionError(f"Credenciales Gemini inválidas: {e}") from e
        except self._genai_errors.ServerError as e:
            raise LLMConexionError(f"Servicio Gemini no disponible: {e}") from e
        except Exception as e:
            raise LLMError(f"Error al llamar a Gemini: {e}") from e
