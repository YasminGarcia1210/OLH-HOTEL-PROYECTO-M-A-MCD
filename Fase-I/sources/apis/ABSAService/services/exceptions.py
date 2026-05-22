"""
Excepciones de dominio del servicio ABSA (Aspect-Based Sentiment Analysis).

La capa de rutas solo captura estas excepciones, nunca las de librerías
externas (psycopg2, openai, google-generativeai, requests, etc.). Esto
desacopla la lógica de negocio de los detalles de implementación.
"""


# ── Pipeline ABSA ─────────────────────────────────────────────────────────────

class ABSAError(Exception):
    """Error base para cualquier fallo en el pipeline ABSA."""


class ArchivoNoEncontradoError(ABSAError):
    """El archivo solicitado no existe en la base de datos."""


class EstadoInvalidoError(ABSAError):
    """El archivo no está en el estado requerido para ejecutar ABSA."""


class ArchivoYaProcesadoError(ABSAError):
    """El archivo ya fue procesado por el pipeline ABSA (estado = 'topicado')."""


class OpenaiBatchPendienteError(ABSAError):
    """Hay un trabajo OpenAI Batch pendiente de sincronizar para este archivo."""


class OpenaiBatchJobNoEncontradoError(ABSAError):
    """No existe un registro pendiente para el openai_batch_id indicado."""


# ── Modelo ────────────────────────────────────────────────────────────────────

class ModeloNoDisponibleError(ABSAError):
    """No se pudo cargar o acceder al modelo ABSA (backend o proveedor no disponible)."""

# ── LLM ──────────────────────────────────────────────────────────────────────

class LLMError(ABSAError):
    """Error base para cualquier fallo al interactuar con el LLM."""


class LLMConexionError(LLMError):
    """No se pudo establecer conexión con el proveedor LLM (red, URL inválida, etc.)."""


class LLMAutenticacionError(LLMError):
    """La API key o credenciales del proveedor LLM son inválidas o están vencidas."""


class RespuestaLLMInvalidaError(LLMError):
    """El LLM respondió con contenido que no pudo parsearse como JSON válido."""
