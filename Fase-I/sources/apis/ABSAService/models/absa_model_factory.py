"""
Factory de modelos ABSA.

Selecciona el backend según Config.ABSA_MODEL_BACKEND:
  "llm"     — LLM (OpenAI / Gemini / Ollama): zero-shot, máxima calidad
  "deberta" — NLI (detección) + DeBERTa ATSC (sentimiento) + BERTopic (dinámicos)

Para el backend "llm", el proveedor se elige con Config.LLM_PROVIDER.
"""

import logging

from models.absa_llm_model import ABSALLMModel
from services.exceptions import ModeloNoDisponibleError

logger = logging.getLogger(__name__)


def crear_modelo(config):
    """
    Instancia y retorna el modelo ABSA configurado.

    Lanza:
        ModeloNoDisponibleError si el backend no es válido.
        DependenciaNoInstalada  si un backend ML requiere deps no instaladas.
    """
    backend = config.ABSA_MODEL_BACKEND

    if backend == "llm":
        llm = _crear_proveedor_llm(config)
        logger.info("Modelo ABSA: backend=llm, version=%s", llm.version)
        return ABSALLMModel(llm)

    if backend == "deberta":
        from models.absa_deberta_model import ABSADebertaModel
        modelo = ABSADebertaModel(config)
        logger.info("Modelo ABSA: backend=deberta, version=%s", modelo.version)
        return modelo

    raise ModeloNoDisponibleError(
        f"Backend ABSA desconocido: '{backend}'. "
        "Valores válidos: 'llm', 'deberta'."
    )


def _crear_proveedor_llm(config):
    """Instancia el proveedor LLM según LLM_PROVIDER."""
    proveedor = config.LLM_PROVIDER

    if proveedor == "openai":
        from services.llm.openai_llm import OpenAILLM
        return OpenAILLM(config)

    if proveedor == "gemini":
        from services.llm.gemini_llm import GeminiLLM
        return GeminiLLM(config)

    if proveedor == "ollama":
        from services.llm.ollama_llm import OllamaLLM
        return OllamaLLM(config)

    raise ModeloNoDisponibleError(
        f"Proveedor LLM desconocido: '{proveedor}'. "
        "Valores válidos: 'openai', 'gemini', 'ollama'."
    )
