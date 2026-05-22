"""
Proveedor LLM: Ollama (servidor local o remoto).

Usa la API REST de Ollama directamente con `requests`.

Requiere:
    OLLAMA_BASE_URL — URL base del servidor (default: http://localhost:11434).
    OLLAMA_MODEL    — modelo a usar (default: llama3.1).
"""

import logging

import requests

from services.exceptions import LLMAutenticacionError, LLMConexionError, LLMError
from services.llm.base import BaseLLM, LLMRespuesta

logger = logging.getLogger(__name__)

_TIMEOUT = 120  # segundos — los modelos locales pueden ser lentos


class OllamaLLM(BaseLLM):

    def __init__(self, config):
        self._base_url   = config.OLLAMA_BASE_URL.rstrip("/")
        self._model_name = config.OLLAMA_MODEL

    @property
    def version(self) -> str:
        return f"llm-ollama-{self._model_name}"

    def completar(self, prompt: str) -> str:
        url = f"{self._base_url}/api/generate"
        payload = {
            "model":  self._model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }

        try:
            resp = requests.post(url, json=payload, timeout=_TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            raise LLMConexionError(f"No se pudo conectar con Ollama en {self._base_url}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise LLMConexionError(f"Timeout al esperar respuesta de Ollama: {e}") from e

        if resp.status_code == 401:
            raise LLMAutenticacionError("Ollama rechazó la solicitud (401).")
        if not resp.ok:
            raise LLMError(f"Ollama respondió con HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
            return LLMRespuesta(
                texto=data.get("response", ""),
                tokens_entrada=data.get("prompt_eval_count", 0),
                tokens_salida=data.get("eval_count", 0),
            )
        except ValueError as e:
            raise LLMError(f"Respuesta de Ollama no es JSON válido: {e}") from e
