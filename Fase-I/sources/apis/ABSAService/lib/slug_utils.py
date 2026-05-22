"""
Utilidades para normalizar texto a slug compatible con la columna topicos.slug.
"""

import re
import unicodedata


def to_slug(nombre: str) -> str:
    """
    Convierte un nombre de tópico libre en un slug en minúsculas, sin acentos
    y con guiones bajos como separador.

    Ejemplos:
        "Desayuno y Gastronomía" → "desayuno_y_gastronomia"
        "Atención al cliente"    → "atencion_al_cliente"
        "WiFi / Internet"        → "wifi_internet"

    La longitud máxima es 60 caracteres (límite de topicos.slug).
    """
    # Normalizar unicode y eliminar diacríticos
    nfkd = unicodedata.normalize("NFKD", nombre.lower())
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")

    # Reemplazar cualquier secuencia de caracteres no alfanuméricos con _
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_str).strip("_")

    return slug[:60]
