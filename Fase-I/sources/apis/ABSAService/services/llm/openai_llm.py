"""
Proveedor LLM: OpenAI.

Requiere:
    OPENAI_API_KEY  — clave de API de OpenAI.
    OPENAI_MODEL    — modelo a usar.
"""

import logging

from services.exceptions import LLMAutenticacionError, LLMConexionError, LLMError
from services.llm.base import BaseLLM, LLMRespuesta

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):

    def __init__(self, config):
        try:
            from openai import OpenAI, AuthenticationError, APIConnectionError, APIError
            self._AuthenticationError = AuthenticationError
            self._APIConnectionError  = APIConnectionError
            self._APIError            = APIError
            self._client = OpenAI(api_key=config.OPENAI_API_KEY)
        except ImportError as e:
            raise LLMError("El paquete 'openai' no está instalado.") from e

        self._model = config.OPENAI_MODEL

    @property
    def version(self) -> str:
        return f"llm-openai-{self._model}"

    def completar(self, prompt: str) -> LLMRespuesta:
        try:
            respuesta = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            uso = respuesta.usage
            return LLMRespuesta(
                texto=respuesta.choices[0].message.content or "",
                tokens_entrada=uso.prompt_tokens if uso else 0,
                tokens_salida=uso.completion_tokens if uso else 0,
            )
        except self._AuthenticationError as e:
            raise LLMAutenticacionError(f"Credenciales OpenAI inválidas: {e}") from e
        except self._APIConnectionError as e:
            raise LLMConexionError(f"No se pudo conectar con OpenAI: {e}") from e
        except self._APIError as e:
            raise LLMError(f"Error de la API de OpenAI: {e}") from e
