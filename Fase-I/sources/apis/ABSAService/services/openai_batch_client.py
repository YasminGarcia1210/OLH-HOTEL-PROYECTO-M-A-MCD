"""
Cliente OpenAI Batch API para chat completions (ABSA).

Sube JSONL, crea batch, consulta estado y descarga salida.
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any

from lib.prompt_builder import construir_prompt
from services.exceptions import LLMAutenticacionError, LLMConexionError, LLMError

logger = logging.getLogger(__name__)


class OpenAIBatchABSAClient:
    """Operaciones Batch API alineadas con OpenAILLM.completar (mismo body por request)."""

    def __init__(self, config):
        self._api_key = getattr(config, "OPENAI_API_KEY", "") or ""
        self._model = getattr(config, "OPENAI_MODEL", "gpt-4o-mini")
        self._client = None
        self._AuthenticationError = None
        self._APIConnectionError = None
        self._APIError = None

    def _client_openai(self):
        if self._client is not None:
            return self._client
        try:
            from openai import APIConnectionError, APIError, AuthenticationError, OpenAI
        except ImportError as e:
            raise LLMError("El paquete 'openai' no está instalado.") from e

        self._AuthenticationError = AuthenticationError
        self._APIConnectionError = APIConnectionError
        self._APIError = APIError
        self._client = OpenAI(api_key=self._api_key)
        return self._client

    def construir_linea_jsonl(
        self,
        review_id: int,
        texto: str,
        topicos_fijos: list[dict],
        topicos_adicionales: list[dict] | None,
    ) -> str:
        prompt = construir_prompt(texto, topicos_fijos, topicos_adicionales)
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        obj = {
            "custom_id": str(review_id),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        }
        return json.dumps(obj, ensure_ascii=False)

    def subir_jsonl_y_crear_batch(self, lineas_jsonl: list[str]) -> tuple[str, str, str]:
        """
        Sube el archivo JSONL y crea el batch.

        Returns:
            (input_file_id, batch_id, estado_openai inicial)
        """
        client = self._client_openai()
        contenido = ("\n".join(lineas_jsonl) + "\n").encode("utf-8")
        buf = io.BytesIO(contenido)
        buf.name = "absa_batch_input.jsonl"

        try:
            uploaded = client.files.create(file=buf, purpose="batch")
            batch = client.batches.create(
                input_file_id=uploaded.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
            )
            return uploaded.id, batch.id, getattr(batch, "status", None) or "validating"
        except self._AuthenticationError as e:
            raise LLMAutenticacionError(f"Credenciales OpenAI inválidas: {e}") from e
        except self._APIConnectionError as e:
            raise LLMConexionError(f"No se pudo conectar con OpenAI: {e}") from e
        except self._APIError as e:
            raise LLMError(f"Error de la API de OpenAI (batch): {e}") from e

    def obtener_batch(self, openai_batch_id: str) -> Any:
        client = self._client_openai()
        try:
            return client.batches.retrieve(openai_batch_id)
        except self._AuthenticationError as e:
            raise LLMAutenticacionError(f"Credenciales OpenAI inválidas: {e}") from e
        except self._APIConnectionError as e:
            raise LLMConexionError(f"No se pudo conectar con OpenAI: {e}") from e
        except self._APIError as e:
            raise LLMError(f"Error de la API de OpenAI (batch retrieve): {e}") from e

    def descargar_texto_archivo(self, file_id: str) -> str:
        client = self._client_openai()
        try:
            resp = client.files.content(file_id)
            return resp.text
        except self._AuthenticationError as e:
            raise LLMAutenticacionError(f"Credenciales OpenAI inválidas: {e}") from e
        except self._APIConnectionError as e:
            raise LLMConexionError(f"No se pudo conectar con OpenAI: {e}") from e
        except self._APIError as e:
            raise LLMError(f"Error de la API de OpenAI (files.content): {e}") from e
