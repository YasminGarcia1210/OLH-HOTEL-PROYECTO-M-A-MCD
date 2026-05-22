"""
Servicio de limpieza de texto para reviews de hoteles.

Responsabilidades:
  - Cargar los parámetros del pipeline desde config/pipeline.yaml.
  - Invocar run_pipeline() de lib/cleaning_pipeline.py sobre el DataFrame validado.
  - Aislar la ruta del resto del sistema: la ruta solo conoce las excepciones
    de dominio de services/exceptions.py, nunca las de las librerías internas.
  - Garantizar que el pipeline siempre reciba las columnas que espera, añadiendo
    una columna de etiqueta temporal si el CSV de entrada no la trae.

Notas de diseño:
  - La configuración se carga una sola vez al instanciar el servicio (lazy=False)
    para detectar errores de configuración en el arranque, no en runtime.
  - ruta_auditoria=None evita que el pipeline escriba ficheros en disco.
"""

import logging
import os

import pandas as pd
import yaml

from lib.cleaning_pipeline import run_pipeline
from services.exceptions import PipelineLimpiezaError, PipelineSinResultadosError

logger = logging.getLogger(__name__)

# Ruta al archivo de configuración (relativa a la raíz del proyecto)
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "pipeline.yaml")

# Columna de etiqueta que espera el pipeline para la deduplicación
_COL_ETIQUETA     = "sentimiento"
_ETIQUETA_DEFAULT = "sin_etiqueta"


class ResultadoLimpieza:
    """Resultado devuelto por el servicio con el DataFrame limpio y estadísticas."""

    def __init__(self, df: pd.DataFrame, total_entrada: int, total_salida: int):
        self.df            = df
        self.total_entrada = total_entrada
        self.total_salida  = total_salida

    @property
    def descartadas(self) -> int:
        return self.total_entrada - self.total_salida


class CleaningService:

    def __init__(self, perfil: str = "prediccion"):
        """
        Parámetros:
            perfil: sección del YAML a cargar ('prediccion' o 'entrenamiento').
        """
        self._config = _cargar_config(perfil)
        logger.info(
            "CleaningService inicializado con perfil '%s': %s",
            perfil, self._config
        )

    def limpiar(self, df: pd.DataFrame, col_texto: str = "review") -> ResultadoLimpieza:
        """
        Ejecuta el pipeline de limpieza completo sobre el DataFrame recibido.

        Parámetros:
            df:        DataFrame ya validado por CsvValidatorService.
            col_texto: Nombre de la columna de texto (por defecto 'review').

        Retorna:
            ResultadoLimpieza con el DataFrame limpio y las estadísticas.

        Lanza:
            PipelineSinResultadosError: si tras la limpieza no quedan filas.
            PipelineLimpiezaError:      para cualquier otro error del pipeline.
        """
        total_entrada = len(df)
        cfg = self._config
        logger.info("Iniciando pipeline de limpieza sobre %d filas (perfil: %s).", total_entrada, cfg)

        # ── Garantizar columna de etiqueta ────────────────────────
        etiqueta_temporal = False
        if _COL_ETIQUETA not in df.columns:
            df = df.copy()
            df[_COL_ETIQUETA] = _ETIQUETA_DEFAULT
            etiqueta_temporal = True

        # ── Ejecutar pipeline ─────────────────────────────────────
        try:
            df_limpio = run_pipeline(
                df,
                col_texto=col_texto,
                col_etiqueta=_COL_ETIQUETA,
                modo=cfg["modo"],
                deduplicar=cfg["deduplicar"],
                umbral_fuzzy=cfg["umbral_fuzzy"],
                filtrar_idioma=cfg["filtrar_idioma"],
                umbral_confianza_idioma=cfg["umbral_confianza_idioma"],
                solo_idioma=cfg["solo_idioma"],
                anonimizar=cfg["anonimizar"],
                nombres=cfg["nombres"],
                min_palabras=cfg["min_palabras"],
                min_tokens=cfg["min_tokens"],
                max_tokens=cfg["max_tokens"],
                ruta_auditoria=None,
            )
        except Exception as e:
            raise PipelineLimpiezaError(
                f"El pipeline de limpieza falló durante su ejecución: {e}"
            ) from e

        # ── Eliminar columna temporal si fue añadida ──────────────
        if etiqueta_temporal and _COL_ETIQUETA in df_limpio.columns:
            df_limpio = df_limpio.drop(columns=[_COL_ETIQUETA])

        # ── Validar que haya datos de salida ──────────────────────
        total_salida = len(df_limpio)
        if total_salida == 0:
            raise PipelineSinResultadosError(
                f"El pipeline eliminó todas las filas ({total_entrada} de entrada). "
                "Revisa el archivo de origen o los parámetros del pipeline."
            )

        logger.info(
            "Pipeline completado: %d filas entrada -> %d filas salida (%d descartadas).",
            total_entrada, total_salida, total_entrada - total_salida
        )

        return ResultadoLimpieza(
            df=df_limpio,
            total_entrada=total_entrada,
            total_salida=total_salida,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cargar_config(perfil: str) -> dict:
    """
    Carga el perfil indicado desde config/pipeline.yaml.
    Lanza un error claro si el archivo o el perfil no existen.
    """
    ruta = os.path.normpath(_CONFIG_PATH)

    if not os.path.isfile(ruta):
        raise FileNotFoundError(
            f"No se encontró el archivo de configuración del pipeline: '{ruta}'"
        )

    with open(ruta, encoding="utf-8") as f:
        contenido = yaml.safe_load(f)

    perfiles = contenido.get("pipeline", {})
    if perfil not in perfiles:
        disponibles = list(perfiles.keys())
        raise KeyError(
            f"Perfil '{perfil}' no encontrado en pipeline.yaml. "
            f"Perfiles disponibles: {disponibles}"
        )

    return perfiles[perfil]
