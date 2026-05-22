# Guía de uso: `cleaning_pipeline.py`

Pipeline de limpieza de texto para reviews de hoteles en español, orientado a modelos de análisis de sentimiento basados en BERT/LLMs.

---

## Índice

1. [Dependencias e instalación](#1-dependencias-e-instalación)
2. [Uso como módulo Python](#2-uso-como-módulo-python)
3. [Uso desde línea de comandos](#3-uso-desde-línea-de-comandos)
4. [Parámetros de `run_pipeline`](#4-parámetros-de-run_pipeline)
5. [Descripción de cada paso del pipeline](#5-descripción-de-cada-paso-del-pipeline)
6. [Funciones auxiliares disponibles](#6-funciones-auxiliares-disponibles)
7. [Modos de limpieza: `bert` vs `clasico`](#7-modos-de-limpieza-bert-vs-clasico)
8. [Salidas y archivos generados](#8-salidas-y-archivos-generados)
9. [Ejemplos completos](#9-ejemplos-completos)

---

## 1. Dependencias e instalación

### Librerías Python requeridas

Todas las dependencias están listadas en el archivo `requirements.txt` incluido en la misma carpeta. Para instalarlas todas de una vez:

```bash
pip install -r requirements.txt
```

El archivo contiene:

```
pandas>=2.3.3
chardet>=7.3.0
emoji>=2.15.0
beautifulsoup4>=4.14.3
lingua-language-detector>=2.2.0
rapidfuzz>=3.14.3
transformers>=5.3.0
spacy>=3.8.13
```

También se pueden instalar manualmente:

```bash
pip install pandas chardet emoji beautifulsoup4 lingua-language-detector rapidfuzz transformers spacy
```

### Modelo de spaCy (anonimización de nombres)

```bash
python -m spacy download es_core_news_sm
```

### Modelo BERT usado internamente

El tokenizador se descarga automáticamente desde HuggingFace la primera vez que se ejecuta:

```
dccuchile/bert-base-spanish-wwm-cased
```

> **Nota:** Se requiere conexión a internet en la primera ejecución para descargar el tokenizador BERT.

---

## 2. Uso como módulo Python

### Importación básica

```python
from cleaning_pipeline import run_pipeline

df_limpio = run_pipeline(df, col_texto="review", col_etiqueta="sentimiento")
```

### Ejemplo con carga de CSV

```python
import pandas as pd
from cleaning_pipeline import detectar_encoding, run_pipeline

# 1. Detectar encoding del archivo
ruta = "data/reviews_hoteles.csv"
enc = detectar_encoding(ruta)

# 2. Cargar el dataset
df = pd.read_csv(ruta, encoding=enc)
print(f"Filas cargadas: {len(df)}")

# 3. Ejecutar el pipeline completo
df_limpio = run_pipeline(
    df,
    col_texto="review",
    col_etiqueta="sentimiento",
    modo="bert",
)

# 4. Guardar resultado
df_limpio.to_csv("data/reviews_limpias.csv", index=False, encoding="utf-8")
```

---

## 3. Uso desde línea de comandos

El script se puede ejecutar directamente desde la terminal:

```bash
python cleaning_pipeline.py --input data/reviews_raw.csv --output data/reviews_clean.csv
```

### Argumentos disponibles

| Argumento        | Obligatorio | Por defecto   | Descripción                                      |
|------------------|:-----------:|:-------------:|--------------------------------------------------|
| `--input`        | ✅           | —             | Ruta del archivo CSV de entrada                  |
| `--output`       | ✅           | —             | Ruta del archivo CSV de salida                   |
| `--col_texto`    | ❌           | `review`      | Nombre de la columna con el texto                |
| `--col_etiqueta` | ❌           | `sentimiento` | Nombre de la columna de etiqueta                 |
| `--modo`         | ❌           | `bert`        | Modo de limpieza: `bert` o `clasico`             |
| `--no_nombres`   | ❌           | (desactivado) | Si se incluye, desactiva la anonimización de nombres propios |

### Ejemplos de uso por CLI

```bash
# Uso mínimo
python cleaning_pipeline.py --input reviews.csv --output reviews_clean.csv

# Especificando columnas y modo
python cleaning_pipeline.py \
  --input datos/reviews_raw.csv \
  --output datos/reviews_clean.csv \
  --col_texto texto \
  --col_etiqueta label \
  --modo clasico

# Sin anonimización de nombres (más rápido)
python cleaning_pipeline.py \
  --input reviews.csv \
  --output reviews_clean.csv \
  --no_nombres
```

---

## 4. Parámetros de `run_pipeline`

```python
run_pipeline(
    df,
    col_texto              = "review",
    col_etiqueta           = "sentimiento",
    modo                   = "bert",
    umbral_fuzzy           = 90,
    umbral_confianza_idioma= 0.75,
    solo_idioma            = "es",
    anonimizar             = True,
    nombres                = True,
    min_tokens             = 6,
    max_tokens             = 512,
    n_head_tokens          = 128,
    ruta_auditoria         = "reviews_eliminadas_cortas.csv",
)
```

| Parámetro                  | Tipo     | Por defecto                        | Descripción |
|----------------------------|----------|------------------------------------|-------------|
| `df`                       | DataFrame| —                                  | DataFrame de entrada con al menos la columna `col_texto` |
| `col_texto`                | str      | `"review"`                         | Nombre de la columna que contiene el texto |
| `col_etiqueta`             | str      | `"sentimiento"`                    | Nombre de la columna de etiqueta de sentimiento |
| `modo`                     | str      | `"bert"`                           | `"bert"` conserva tildes y ñ; `"clasico"` las elimina |
| `umbral_fuzzy`             | int      | `90`                               | Similitud mínima (0–100) para detectar casi-duplicados |
| `umbral_confianza_idioma`  | float    | `0.75`                             | Confianza mínima del detector de idioma (0.0–1.0) |
| `solo_idioma`              | str      | `"es"`                             | Código ISO 639-1 del idioma a conservar |
| `anonimizar`               | bool     | `True`                             | Enmascara emails, teléfonos y tarjetas de crédito |
| `nombres`                  | bool     | `True`                             | Anonimiza nombres propios con spaCy (`[PERSONA]`) |
| `min_tokens`               | int      | `6`                                | Reviews con menos tokens son eliminadas |
| `max_tokens`               | int      | `512`                              | Límite máximo de tokens (límite de BERT); textos más largos se truncan |
| `n_head_tokens`            | int      | `128`                              | Tokens del inicio conservados al truncar (estrategia head+tail) |
| `ruta_auditoria`           | str/None | `"reviews_eliminadas_cortas.csv"`  | Ruta donde se guardan las filas eliminadas por ser muy cortas; `None` para desactivar |

---

## 5. Descripción de cada paso del pipeline

El pipeline ejecuta **8 pasos** en orden secuencial:

### Paso 1 — Reparación de encoding
Corrige el problema de doble codificación **latin-1 → utf-8**, frecuente en archivos scrapeados. Por ejemplo, `Ã±` se convierte en `ñ`.

### Paso 2 — Eliminación de duplicados
- **Duplicados exactos:** Se normalizan los textos (minúsculas, sin tildes, sin puntuación) y se eliminan duplicados exactos.
- **Casi-duplicados (fuzzy):** Se usa `RapidFuzz` para detectar pares de textos con similitud ≥ `umbral_fuzzy`. Este paso solo se aplica si el dataset tiene ≤ 15,000 filas (costo computacional O(n²)).
- Detecta y reporta textos que son duplicados pero tienen **etiquetas inconsistentes**.

### Paso 3 — Filtro de idioma
Usa la librería `Lingua` para detectar el idioma de cada review y su nivel de confianza. Las reviews se clasifican en:

| Categoría        | Descripción |
|------------------|-------------|
| `idioma_seguro`  | Idioma correcto con confianza suficiente → **se conservan** |
| `idioma_dudoso`  | Idioma correcto pero baja confianza → eliminadas |
| `otro_idioma`    | Otro idioma detectado con alta confianza → eliminadas |
| `muy_corto`      | Texto demasiado corto para detectar idioma → eliminadas |

### Paso 4 — Limpieza de HTML y entidades
- Decodifica entidades HTML (`&amp;`, `&nbsp;`, `&#34;`, etc.).
- Elimina etiquetas HTML usando `BeautifulSoup`.

### Paso 5 — Caracteres especiales y espacios
- Elimina caracteres de control invisibles.
- Normaliza comillas tipográficas (`"` → `"`), guiones largos (`—` → `-`), etc.
- Según el `modo`, conserva o elimina tildes y ñ.
- Normaliza espacios múltiples y saltos de línea redundantes.

### Paso 6 — Procesamiento de emojis
- Convierte emoticones de texto (`:)`, `:(`, `:D`, etc.) a tokens legibles (`cara_feliz`, `cara_triste`...).
- Colapsa emojis repetidos (tres o más iguales añaden la palabra ` mucho `).
- En modo `bert`: convierte emojis Unicode a su descripción en español (via `emoji.demojize`).
- En modo `clasico`: elimina todos los emojis.

### Paso 7 — Ruido estructural
Aplica en orden:
1. **URLs:** Elimina `http://`, `https://` y `www.`.
2. **Datos personales:** Reemplaza emails (`[EMAIL]`), teléfonos (`[TELEFONO]`) y números de tarjeta (`[TARJETA]`).
3. **Menciones y hashtags:** En modo `bert` conserva el texto del hashtag (sin `#`); elimina menciones `@usuario`.
4. **Números:** En modo `bert` elimina números de habitación, fechas y números de 6+ dígitos. En modo `clasico` reemplaza todos los números por `[NUM]`.
5. **Nombres propios:** Detecta entidades `PER` con spaCy y las reemplaza por `[PERSONA]`.
6. **Filtro de longitud mínima:** Elimina filas que queden con menos de `min_palabras` (default: 5 palabras).

### Paso 8 — Control de longitud (tokens BERT)
- Cuenta tokens reales usando el tokenizador `dccuchile/bert-base-spanish-wwm-cased`.
- Elimina reviews con menos de `min_tokens` tokens (guarda auditoría en CSV si se indica).
- Trunca reviews largas con la estrategia **head + tail**: conserva los primeros `n_head_tokens` y los últimos tokens hasta completar `max_tokens`.

---

## 6. Funciones auxiliares disponibles

Además del pipeline completo, se pueden usar las funciones individuales:

```python
from cleaning_pipeline import (
    detectar_encoding,          # Detecta encoding de un archivo CSV
    reparar_encoding_roto,      # Repara doble-encoding en un texto
    limpiar_duplicados,         # Deduplicación exacta + fuzzy
    filtrar_por_idioma,         # Filtro de idioma con Lingua
    limpiar_html,               # Limpieza de HTML y entidades
    limpiar_caracteres,         # Limpieza de caracteres especiales
    normalizar_espacios,        # Normalización de espacios
    procesar_emojis,            # Conversión/eliminación de emojis
    limpiar_urls,               # Eliminación de URLs
    anonimizar_datos_personales,# Enmascaramiento de email/teléfono/tarjeta
    limpiar_menciones_hashtags, # Limpieza de @ y #
    procesar_numeros,           # Tratamiento de números
    anonimizar_nombres,         # Anonimización de nombres propios (spaCy)
    limpiar_ruido_estructural,  # Paso 7 completo sobre DataFrame
    manejar_longitudes,         # Control de tokens BERT
)
```

### Ejemplo: usar solo la detección de encoding

```python
from cleaning_pipeline import detectar_encoding
import pandas as pd

enc = detectar_encoding("mi_archivo.csv")
df = pd.read_csv("mi_archivo.csv", encoding=enc)
```

### Ejemplo: aplicar solo la limpieza de emojis

```python
from cleaning_pipeline import procesar_emojis

texto = "¡Excelente hotel! 😍😍😍 Todo perfecto :)"
limpio = procesar_emojis(texto, modo="bert")
# Resultado: "¡Excelente hotel! cara_encantada mucho Todo perfecto  cara_feliz"
```

---

## 7. Modos de limpieza: `bert` vs `clasico`

| Característica                      | `bert` (recomendado)          | `clasico`               |
|-------------------------------------|-------------------------------|-------------------------|
| Tildes y ñ                          | Se conservan                  | Se eliminan             |
| Emojis                              | Convertidos a texto en español| Eliminados              |
| Hashtags                            | Se conserva el texto (`#hotel` → `hotel`) | Se eliminan completamente |
| Números                             | Solo elimina fechas y IDs largos | Todos → `[NUM]`      |
| Caracteres especiales               | Conserva `.,;:!?¡¿-'"()`     | Conjunto más reducido   |
| **Cuándo usar**                     | Modelos BERT/Transformers     | Modelos clásicos (TF-IDF, Naive Bayes, etc.) |

---

## 8. Salidas y archivos generados

| Archivo                              | Cuándo se genera |
|--------------------------------------|------------------|
| `reviews_eliminadas_cortas.csv`      | Cuando hay reviews eliminadas por ser demasiado cortas (configurable con `ruta_auditoria`) |
| DataFrame de salida (`run_pipeline`) | Siempre; contiene las mismas columnas que el original, con el texto limpio |

El DataFrame de salida mantiene las **mismas columnas** del DataFrame de entrada. No se agregan columnas adicionales.

---

## 9. Ejemplos completos

### Ejemplo 1: Pipeline estándar para fine-tuning de BERT

```python
import pandas as pd
from cleaning_pipeline import detectar_encoding, run_pipeline

ruta_entrada = "data/reviews_hoteles_raw.csv"
ruta_salida  = "data/reviews_hoteles_clean.csv"

enc = detectar_encoding(ruta_entrada)
df  = pd.read_csv(ruta_entrada, encoding=enc)

df_limpio = run_pipeline(
    df,
    col_texto    = "review",
    col_etiqueta = "sentimiento",
    modo         = "bert",
    min_tokens   = 10,
    max_tokens   = 512,
    n_head_tokens= 128,
    ruta_auditoria = "auditoria_cortas.csv",
)

df_limpio.to_csv(ruta_salida, index=False, encoding="utf-8")
print(f"Dataset limpio: {len(df_limpio)} filas guardadas en {ruta_salida}")
```

### Ejemplo 2: Pipeline rápido sin anonimización de nombres

```python
df_limpio = run_pipeline(
    df,
    col_texto  = "comentario",
    col_etiqueta = "label",
    modo       = "bert",
    nombres    = False,         # Omite el paso de spaCy (más rápido)
    anonimizar = True,          # Pero sí enmascara emails y teléfonos
    ruta_auditoria = None,      # No genera archivo de auditoría
)
```

### Ejemplo 3: Pipeline para modelo clásico (sin BERT)

```python
df_limpio = run_pipeline(
    df,
    col_texto    = "review",
    col_etiqueta = "stars",
    modo         = "clasico",   # Elimina tildes, normaliza todo
    min_tokens   = 5,
    max_tokens   = 512,
)
```

### Ejemplo 4: Dataset en inglés

```python
df_limpio = run_pipeline(
    df,
    col_texto    = "review_text",
    col_etiqueta = "rating",
    modo         = "bert",
    solo_idioma  = "en",         # Filtra solo reviews en inglés
    umbral_confianza_idioma = 0.80,
)
```

### Ejemplo 5: Deduplicación más estricta

```python
df_limpio = run_pipeline(
    df,
    col_texto    = "review",
    col_etiqueta = "sentimiento",
    umbral_fuzzy = 80,  # Más agresivo: detecta similitudes desde 80%
)
```

---

## Estructura esperada del CSV de entrada

El CSV de entrada debe contener al menos una columna de texto. Una columna de etiqueta es recomendable para la deduplicación consistente.

```
review,sentimiento
"El hotel fue excelente, muy limpio y cómodo.",positivo
"Pésimo servicio, habitaciones sucias.",negativo
"Buena ubicación pero camas incómodas.",neutro
```

> Las columnas adicionales (hotel, fecha, puntuación, etc.) se conservan intactas en el DataFrame de salida.
