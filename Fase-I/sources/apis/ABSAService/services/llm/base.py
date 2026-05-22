"""
Interfaz abstracta para proveedores LLM.

Cada proveedor (OpenAI, Gemini, Ollama) implementa esta clase.
La capa de modelo ABSA solo depende de esta interfaz, no de SDKs concretos.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMRespuesta:
    texto:          str
    tokens_entrada: int = 0
    tokens_salida:  int = 0


class BaseLLM(ABC):

    @abstractmethod
    def completar(self, prompt: str) -> LLMRespuesta:
        """
        Envía el prompt al LLM y retorna texto y uso de tokens.

        Lanza:
            LLMConexionError      si no hay conexión con el proveedor.
            LLMAutenticacionError si las credenciales son inválidas.
            LLMError              para cualquier otro fallo del proveedor.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Identificador del modelo utilizado, para almacenar en modelo_version.
        Ejemplo: "llm-openai-gpt-4o-mini", "llm-ollama-llama3.1"
        """
