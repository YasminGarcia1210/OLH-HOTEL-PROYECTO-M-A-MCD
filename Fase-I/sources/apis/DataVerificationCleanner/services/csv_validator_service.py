"""
Servicio de validación de estructura y contenido del CSV de reviews.

Responsabilidades:
  - Verificar que el archivo pueda parsearse como CSV válido.
  - Confirmar que existen las columnas requeridas.
  - Calcular estadísticas básicas: total de filas, filas válidas y descartadas.
  - Retornar el DataFrame limpio listo para el siguiente paso del pipeline.

La ruta nunca importa pandas directamente. Solo conoce las excepciones
de dominio definidas en services/exceptions.py.
"""

import io
import logging

import pandas as pd

from services.exceptions import CsvEstructuraInvalidaError, CsvSinDatosError

logger = logging.getLogger(__name__)

# Columnas que debe tener el CSV de entrada
COLUMNAS_REQUERIDAS = {"review", "fecha"}

# Columnas opcionales que se usarán si están presentes
COLUMNAS_OPCIONALES = {"sentimiento", "idioma"}

# Porcentaje máximo de filas con texto de review vacío permitido (0.5 = 50%)
MAX_PORCENTAJE_VACIOS = 0.5


class ResultadoValidacion:
    """Resultado devuelto por el validador con el DataFrame y las estadísticas."""

    def __init__(self, df: pd.DataFrame, total: int, validas: int, descartadas: int):
        self.df          = df
        self.total       = total
        self.validas     = validas
        self.descartadas = descartadas


class CsvValidatorService:

    def validar(self, contenido: io.BytesIO) -> ResultadoValidacion:
        """
        Valida la estructura y el contenido del CSV recibido como BytesIO.

        Parámetros:
            contenido: BytesIO con el contenido descargado desde Azure Blob Storage.

        Retorna:
            ResultadoValidacion con el DataFrame filtrado y las estadísticas.

        Lanza:
            CsvEstructuraInvalidaError: si no puede parsearse o faltan columnas.
            CsvSinDatosError: si el archivo no tiene filas utilizables.
        """
        # ── 1. Parsear CSV ────────────────────────────────────────
        contenido.seek(0)
        try:
            df = pd.read_csv(contenido, encoding="utf-8")
        except UnicodeDecodeError:
            contenido.seek(0)
            try:
                df = pd.read_csv(contenido, encoding="latin-1")
                logger.warning("El CSV fue leído con encoding latin-1 (no es UTF-8).")
            except Exception as e:
                raise CsvEstructuraInvalidaError(
                    f"El archivo no pudo ser leído como CSV: {e}"
                ) from e
        except Exception as e:
            raise CsvEstructuraInvalidaError(
                f"El archivo no pudo ser leído como CSV: {e}"
            ) from e

        # ── 2. Normalizar nombres de columnas ─────────────────────
        df.columns = [col.strip().lower() for col in df.columns]

        # ── 3. Verificar columnas requeridas ──────────────────────
        columnas_presentes   = set(df.columns)
        columnas_faltantes   = COLUMNAS_REQUERIDAS - columnas_presentes

        if columnas_faltantes:
            raise CsvEstructuraInvalidaError(
                f"Columnas requeridas ausentes: {sorted(columnas_faltantes)}. "
                f"Columnas encontradas: {sorted(columnas_presentes)}"
            )

        logger.info(
            "Estructura válida. Columnas encontradas: %s",
            sorted(columnas_presentes)
        )

        # ── 4. Verificar que haya datos ───────────────────────────
        total = len(df)
        if total == 0:
            raise CsvSinDatosError("El archivo CSV no contiene filas de datos.")

        # ── 5. Validar columna fecha: obligatoria en todos los registros ──
        fechas_nulas = df["fecha"].isna() | (df["fecha"].astype(str).str.strip() == "")
        if fechas_nulas.any():
            cantidad = int(fechas_nulas.sum())
            filas    = df.index[fechas_nulas].tolist()[:5]
            raise CsvEstructuraInvalidaError(
                f"La columna 'fecha' es obligatoria y tiene {cantidad} fila(s) sin valor. "
                f"Primeras filas afectadas (índice): {filas}"
            )

        fechas_parseadas = pd.to_datetime(df["fecha"], format="ISO8601", errors="coerce")
        fechas_invalidas = fechas_parseadas.isna()
        if fechas_invalidas.any():
            cantidad = int(fechas_invalidas.sum())
            ejemplos = df.loc[fechas_invalidas, "fecha"].head(3).tolist()
            raise CsvEstructuraInvalidaError(
                f"La columna 'fecha' tiene {cantidad} valor(es) que no cumplen el formato ISO 8601 "
                f"(ej. '2024-01-15' o '2024-01-15T10:30:00'). "
                f"Ejemplos inválidos encontrados: {ejemplos}"
            )

        logger.info("Columna 'fecha' validada: todos los registros tienen fecha ISO válida.")

        # ── 6. Filtrar filas con texto de review vacío ────────────
        mascara_validas = df["review"].notna() & (df["review"].str.strip() != "")
        df_valido       = df[mascara_validas].copy()

        validas     = len(df_valido)
        descartadas = total - validas

        # ── 7. Validar porcentaje mínimo de datos útiles ──────────
        porcentaje_vacios = descartadas / total
        if porcentaje_vacios > MAX_PORCENTAJE_VACIOS:
            raise CsvSinDatosError(
                f"El {porcentaje_vacios:.0%} de las filas tiene el campo 'review' vacío "
                f"({descartadas} de {total}). El umbral máximo permitido es {MAX_PORCENTAJE_VACIOS:.0%}."
            )

        logger.info(
            "Validación completada: %d filas totales, %d válidas, %d descartadas.",
            total, validas, descartadas
        )

        return ResultadoValidacion(
            df=df_valido,
            total=total,
            validas=validas,
            descartadas=descartadas
        )
