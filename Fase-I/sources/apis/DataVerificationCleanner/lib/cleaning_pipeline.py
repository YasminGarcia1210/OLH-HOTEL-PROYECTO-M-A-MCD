"""
Pipeline de limpieza de texto para reviews de hoteles en español.
Orientado a modelos de sentimiento (BERT/LLMs).

Uso:
    from cleaning_pipeline import run_pipeline
    df_limpio = run_pipeline(df, col_texto="review", col_etiqueta="sentimiento")
"""

import re
import html
import unicodedata
from collections import Counter

import pandas as pd
import chardet
import emoji
from bs4 import BeautifulSoup
from lingua import Language, LanguageDetectorBuilder
from rapidfuzz import fuzz
from transformers import AutoTokenizer
import spacy


# ---------------------------------------------------------------------------
# Configuración global
# ---------------------------------------------------------------------------

_IDIOMAS_DETECTOR = [
    Language.SPANISH,
    Language.ENGLISH,
    Language.FRENCH,
    Language.PORTUGUESE,
    Language.GERMAN,
    Language.ITALIAN,
]

_BERT_MODEL = "dccuchile/bert-base-spanish-wwm-cased"

_REEMPLAZOS_UNICODE = {
    "\u2019": "'",
    "\u2018": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2026": "...",
    "\u00b7": "·",
    "\xa0":   " ",
}

_EMOTICONES = {
    r":\)":  " cara_feliz ",
    r":\(":  " cara_triste ",
    r":D":   " cara_muy_feliz ",
    r"xD":   " cara_riendo ",
    r"=\)":  " cara_feliz ",
    r":\|":  " cara_neutral ",
    r">:\(": " cara_enojada ",
    r";\)":  " guiño ",
    r":/":   " cara_dudosa ",
}


# ---------------------------------------------------------------------------
# 1. Encoding
# ---------------------------------------------------------------------------

def detectar_encoding(ruta_archivo: str) -> str:
    """Detecta el encoding de un archivo CSV."""
    with open(ruta_archivo, "rb") as f:
        muestra = f.read(100_000)
    resultado = chardet.detect(muestra)
    print(f"Encoding detectado: {resultado['encoding']} (confianza: {resultado['confidence']:.0%})")
    return resultado["encoding"]


def reparar_encoding_roto(texto: str) -> str:
    """Repara doble-encoding latin-1 → utf-8 (ej. 'Ã±' → 'ñ')."""
    if not isinstance(texto, str):
        return texto
    try:
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


# ---------------------------------------------------------------------------
# 2. Deduplicación
# ---------------------------------------------------------------------------

def _normalizar_para_comparacion(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = re.sub(r"[^\w\s]", "", texto)
    return texto


def _encontrar_casi_duplicados(textos, umbral: int = 90) -> list[tuple]:
    duplicados = []
    textos = list(textos)
    for i in range(len(textos)):
        for j in range(i + 1, len(textos)):
            score = fuzz.ratio(textos[i], textos[j])
            if score >= umbral:
                duplicados.append((i, j, score))
    return duplicados


def limpiar_duplicados(
    df: pd.DataFrame,
    col_texto: str = "review",
    col_etiqueta: str = "sentimiento",
    umbral_fuzzy: int = 90,
) -> tuple[pd.DataFrame, dict]:
    """
    Elimina duplicados exactos (normalizados) y casi-duplicados por fuzzy matching.
    Retorna el DataFrame limpio y un reporte de estadísticas.
    """
    reporte = {"total_inicial": len(df)}

    df["_norm"] = df[col_texto].apply(_normalizar_para_comparacion)

    conflictos = df[df.duplicated(subset="_norm", keep=False)]
    conflictos_multi = conflictos.groupby("_norm")[col_etiqueta].nunique()
    conflictos_reales = conflictos_multi[conflictos_multi > 1]
    reporte["conflictos_etiqueta"] = len(conflictos_reales)
    if len(conflictos_reales) > 0:
        print(f"  Advertencia: {len(conflictos_reales)} textos con etiquetas inconsistentes.")

    df = df.drop_duplicates(subset="_norm", keep="first").reset_index(drop=True)
    reporte["tras_exactos"] = len(df)

    if len(df) <= 15_000:
        pares = _encontrar_casi_duplicados(df[col_texto], umbral=umbral_fuzzy)
        indices_a_eliminar = {j for _, j, _ in pares}
        df = df.drop(index=list(indices_a_eliminar)).reset_index(drop=True)
        reporte["casi_duplicados_eliminados"] = len(indices_a_eliminar)

    df = df.drop(columns="_norm")
    reporte["total_final"] = len(df)
    reporte["eliminados"] = reporte["total_inicial"] - reporte["total_final"]
    return df, reporte


# ---------------------------------------------------------------------------
# 3. Detección y filtrado de idioma
# ---------------------------------------------------------------------------

def _detectar_con_confianza(texto: str, detector) -> tuple[str, float]:
    if not texto or len(texto.strip()) < 5:
        return "desconocido", 0.0
    resultados = detector.compute_language_confidence_values(texto)
    if not resultados:
        return "desconocido", 0.0
    mejor = resultados[0]
    idioma = mejor.language.iso_code_639_1.name.lower()
    return idioma, round(mejor.value, 3)


def filtrar_por_idioma(
    df: pd.DataFrame,
    col_texto: str = "review",
    umbral_confianza: float = 0.75,
    solo_idioma: str = "es",
    filtrar: bool = True,
) -> pd.DataFrame:
    """
    Detecta el idioma de cada review y agrega la columna 'idioma'.

    Si filtrar=True  → elimina reviews que no sean del idioma indicado
                       o cuya confianza de detección sea menor al umbral.
    Si filtrar=False → solo detecta y agrega 'idioma'; no elimina ninguna fila.
    """
    detector = LanguageDetectorBuilder.from_languages(*_IDIOMAS_DETECTOR).build()

    df[["idioma", "confianza"]] = df[col_texto].apply(
        lambda x: pd.Series(_detectar_con_confianza(x, detector))
    )

    df["categoria_idioma"] = "otros"
    df.loc[
        (df["idioma"] == solo_idioma) & (df["confianza"] >= umbral_confianza),
        "categoria_idioma",
    ] = "idioma_seguro"
    df.loc[
        (df["idioma"] == solo_idioma) & (df["confianza"] < umbral_confianza),
        "categoria_idioma",
    ] = "idioma_dudoso"
    df.loc[
        (df["idioma"] != solo_idioma) & (df["confianza"] >= umbral_confianza),
        "categoria_idioma",
    ] = "otro_idioma"
    df.loc[df["idioma"] == "desconocido", "categoria_idioma"] = "muy_corto"

    total = len(df)
    print("=== Detección de idioma ===")
    for cat, grupo in df.groupby("categoria_idioma"):
        pct = len(grupo) / total * 100
        print(f"  {cat:<20}: {len(grupo):>5} ({pct:.1f}%)")

    if filtrar:
        df = df[df["categoria_idioma"] == "idioma_seguro"].copy()
        print(f"  Dataset tras filtro      : {len(df)} filas")
    else:
        print("  Filtro de idioma desactivado: se conservan todas las filas.")

    df = df.drop(columns=["confianza", "categoria_idioma"])
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Limpieza de HTML y entidades
# ---------------------------------------------------------------------------

def limpiar_html(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    texto = html.unescape(texto)
    if re.search(r"<[^>]+>", texto):
        texto = BeautifulSoup(texto, "html.parser").get_text(separator=" ")
    texto = re.sub(r"&nbsp;", " ", texto)
    texto = re.sub(r"&[a-zA-Z]+;", " ", texto)
    texto = re.sub(r"&#\d+;", " ", texto)
    return texto


# ---------------------------------------------------------------------------
# 5. Limpieza de caracteres especiales
# ---------------------------------------------------------------------------

def limpiar_caracteres(texto: str, modo: str = "bert") -> str:
    """
    modo='bert'    → conserva tildes, ñ y puntuación básica.
    modo='clasico' → elimina tildes, reduce puntuación.
    """
    if not isinstance(texto, str):
        return texto

    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto)

    for orig, reemplazo in _REEMPLAZOS_UNICODE.items():
        texto = texto.replace(orig, reemplazo)

    if modo == "clasico":
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
        texto = re.sub(r"[^a-zA-Z0-9\sáéíóúüñ.,;:!?¡¿\-']", " ", texto)

    elif modo == "bert":
        texto = re.sub(
            r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ.,;:!?¡¿\-'\"()\n]", " ", texto
        )

    return texto


# ---------------------------------------------------------------------------
# 6. Normalización de espacios
# ---------------------------------------------------------------------------

def normalizar_espacios(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    texto = re.sub(r"\n{2,}", "\n", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\s+([.,;:!?])", r"\1", texto)
    return texto.strip()


# ---------------------------------------------------------------------------
# 7. Emojis
# ---------------------------------------------------------------------------

def _colapsar_emojis_repetidos(texto: str) -> str:
    resultado, i, chars = [], 0, list(texto)
    while i < len(chars):
        c = chars[i]
        if c in emoji.EMOJI_DATA:
            count = 1
            while i + count < len(chars) and chars[i + count] == c:
                count += 1
            resultado.append(c)
            if count >= 3:
                resultado.append(" mucho ")
            else:
                resultado.extend([c] * (count - 1))
            i += count
        else:
            resultado.append(c)
            i += 1
    return "".join(resultado)


def procesar_emojis(texto: str, modo: str = "bert") -> str:
    """
    modo='bert'    → convierte emojis a descripción en español.
    modo='clasico' → elimina emojis directamente.
    """
    if not isinstance(texto, str):
        return texto

    for patron, reemplazo in _EMOTICONES.items():
        texto = re.sub(patron, reemplazo, texto, flags=re.IGNORECASE)

    texto = _colapsar_emojis_repetidos(texto)

    if modo == "bert":
        texto = emoji.demojize(texto, language="es")
        texto = re.sub(r":([a-záéíóúüñ_]+):", r" \1 ", texto)
    else:
        texto = emoji.replace_emoji(texto, replace=" ")

    return re.sub(r"[ \t]+", " ", texto).strip()


# ---------------------------------------------------------------------------
# 8. Ruido estructural (URLs, datos personales, números, nombres)
# ---------------------------------------------------------------------------

def limpiar_urls(texto: str, reemplazo: str = "") -> str:
    if not isinstance(texto, str):
        return texto
    return re.sub(r"https?://\S+|www\.\S+", reemplazo, texto).strip()


def anonimizar_datos_personales(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    texto = re.sub(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]", texto
    )
    texto = re.sub(r"\+?\d[\d\s\-().]{7,}\d", "[TELEFONO]", texto)
    texto = re.sub(
        r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b", "[TARJETA]", texto
    )
    return texto


def limpiar_menciones_hashtags(texto: str, modo: str = "bert") -> str:
    if not isinstance(texto, str):
        return texto
    if modo == "bert":
        texto = re.sub(r"#(\w+)", r"\1", texto)
        texto = re.sub(r"@\w+", "", texto)
    else:
        texto = re.sub(r"[#@]\w+", "", texto)
    return texto.strip()


def procesar_numeros(texto: str, modo: str = "bert") -> str:
    if not isinstance(texto, str):
        return texto
    if modo == "bert":
        texto = re.sub(
            r"\b(habitaci[oó]n|room|piso|planta|suite)\s*\d+",
            r"\1", texto, flags=re.IGNORECASE,
        )
        texto = re.sub(r"\b\d{6,}\b", "", texto)
        texto = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "", texto)
        texto = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", texto)
    else:
        texto = re.sub(r"\b\d+([.,]\d+)?\b", "[NUM]", texto)
    return texto


def _cargar_spacy():
    try:
        return spacy.load("es_core_news_ld")
    except OSError:
        print("  Advertencia: modelo spaCy 'es_core_news_sm' no encontrado. "
              "Instálalo con: python -m spacy download es_core_news_sm")
        return None


def anonimizar_nombres(texto: str, nlp) -> str:
    if not isinstance(texto, str) or nlp is None:
        return texto
    doc = nlp(texto)
    resultado = texto
    for ent in reversed(doc.ents):
        if ent.label_ == "PER":
            resultado = (
                resultado[: ent.start_char] + "[PERSONA]" + resultado[ent.end_char :]
            )
    return resultado


def limpiar_ruido_estructural(
    df: pd.DataFrame,
    col: str = "review",
    modo: str = "bert",
    anonimizar: bool = True,
    nombres: bool = True,
    min_palabras: int = 5,
) -> pd.DataFrame:
    df = df.copy()
    nlp = _cargar_spacy() if nombres else None

    df[col] = df[col].apply(limpiar_urls)
    if anonimizar:
        df[col] = df[col].apply(anonimizar_datos_personales)
    df[col] = df[col].apply(lambda x: limpiar_menciones_hashtags(x, modo=modo))
    df[col] = df[col].apply(lambda x: procesar_numeros(x, modo=modo))
    if nombres and nlp is not None:
        df[col] = df[col].apply(lambda x: anonimizar_nombres(x, nlp))

    df[col] = df[col].apply(
        lambda x: re.sub(r"[ \t]+", " ", str(x)).strip() if isinstance(x, str) else x
    )

    antes = len(df)
    df = df[df[col].str.split().str.len() >= min_palabras].reset_index(drop=True)
    print(f"  Filas eliminadas por quedar muy cortas: {antes - len(df)}")
    return df


# ---------------------------------------------------------------------------
# 9. Control de longitud (tokens BERT)
# ---------------------------------------------------------------------------

def _truncar_head_tail(texto: str, tokenizer, max_tokens: int = 512, n_head: int = 128) -> str:
    if not isinstance(texto, str):
        return texto
    tokens = tokenizer.encode(texto, add_special_tokens=False)
    if len(tokens) <= max_tokens - 2:
        return texto
    n_tail = max_tokens - 2 - n_head
    return tokenizer.decode(tokens[:n_head] + tokens[-n_tail:], skip_special_tokens=True)


def manejar_longitudes(
    df: pd.DataFrame,
    col: str = "review",
    min_tokens: int = 6,
    max_tokens: int = 512,
    n_head: int = 128,
    ruta_auditoria: str | None = "reviews_eliminadas_cortas.csv",
) -> pd.DataFrame:
    tokenizer = AutoTokenizer.from_pretrained(_BERT_MODEL)
    df = df.copy()

    df["_n_tokens"] = df[col].apply(
        lambda x: len(tokenizer.encode(str(x), add_special_tokens=True))
    )

    mask_cortos = df["_n_tokens"] < min_tokens
    if ruta_auditoria and mask_cortos.any():
        df[mask_cortos].drop(columns="_n_tokens").to_csv(ruta_auditoria, index=False)
    df = df[~mask_cortos].reset_index(drop=True)

    mask_largos = df["_n_tokens"] > max_tokens
    df.loc[mask_largos, col] = df.loc[mask_largos, col].apply(
        lambda x: _truncar_head_tail(x, tokenizer, max_tokens, n_head)
    )

    df = df.drop(columns="_n_tokens")
    print(f"  Eliminados por cortos: {mask_cortos.sum()} | Truncados: {mask_largos.sum()}")
    return df


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run_pipeline(
    df: pd.DataFrame,
    col_texto: str = "review",
    col_etiqueta: str = "sentimiento",
    modo: str = "bert",
    deduplicar: bool = True,
    umbral_fuzzy: int = 90,
    filtrar_idioma: bool = True,
    umbral_confianza_idioma: float = 0.75,
    solo_idioma: str = "es",
    anonimizar: bool = True,
    nombres: bool = True,
    min_palabras: int = 5,
    min_tokens: int = 6,
    max_tokens: int = 512,
    n_head_tokens: int = 128,
    ruta_auditoria: str | None = "reviews_eliminadas_cortas.csv",
) -> pd.DataFrame:
    """
    Pipeline completo de limpieza de reviews de hoteles.

    Parámetros
    ----------
    df                      : DataFrame de entrada con al menos la columna col_texto.
    col_texto               : Nombre de la columna con el texto de la review.
    col_etiqueta            : Nombre de la columna de etiqueta de sentimiento.
    modo                    : 'bert' (conserva tildes/ñ) o 'clasico' (normaliza todo).
    deduplicar              : Si True, elimina reviews duplicadas/casi-duplicadas.
                              Útil para entrenamiento; desactivar para predicción.
    filtrar_idioma          : Si True, elimina reviews en otros idiomas o con baja confianza.
                              Si False, solo detecta el idioma y lo agrega como columna.
    min_palabras            : Mínimo de palabras que debe tener una review tras limpieza
                              (paso 7). Reviews más cortas se descartan.
                              donde cada review debe conservarse.
    umbral_fuzzy            : Similitud mínima (%) para considerar dos textos casi-duplicados.
    umbral_confianza_idioma : Confianza mínima del detector de idioma para aceptar una review.
    solo_idioma             : Código ISO del idioma que se conserva (p. ej. 'es').
    anonimizar              : Si True, enmascara emails y teléfonos.
    nombres                 : Si True, anonimiza nombres propios con spaCy.
    min_tokens              : Reviews con menos tokens se eliminan.
    max_tokens              : Reviews más largas se truncan (límite de BERT).
    n_head_tokens           : Tokens del inicio que se conservan en el truncado head+tail.
    ruta_auditoria          : Ruta donde guardar las filas eliminadas por ser cortas.

    Retorna
    -------
    pd.DataFrame limpio y listo para entrenamiento o predicción.
    """
    print(f"\n{'='*55}")
    print(f"  PIPELINE DE LIMPIEZA  |  {len(df)} filas de entrada")
    print(f"{'='*55}\n")

    # --- Paso 1: encoding ---
    print("[1/8] Reparando encoding...")
    df = df.copy()
    df[col_texto] = df[col_texto].apply(reparar_encoding_roto)

    # --- Paso 2: deduplicación (solo para entrenamiento) ---
    if deduplicar:
        print("\n[2/8] Eliminando duplicados...")
        df, rep_dup = limpiar_duplicados(df, col_texto, col_etiqueta, umbral_fuzzy)
        print(f"  {rep_dup['eliminados']} registros eliminados "
              f"({rep_dup['total_inicial']} -> {rep_dup['total_final']})")
    else:
        print("\n[2/8] Deduplicacion desactivada (modo prediccion).")

    # --- Paso 3: detección (y filtro opcional) de idioma ---
    print("\n[3/8] Detectando idioma...")
    df = filtrar_por_idioma(
        df, col_texto, umbral_confianza_idioma, solo_idioma,
        filtrar=filtrar_idioma,
    )

    # --- Paso 4: HTML y entidades ---
    print("\n[4/8] Limpiando HTML y entidades...")
    df[col_texto] = df[col_texto].apply(limpiar_html)

    # --- Paso 5: caracteres especiales + espacios ---
    print("\n[5/8] Limpiando caracteres especiales y normalizando espacios...")
    df[col_texto] = df[col_texto].apply(lambda x: limpiar_caracteres(x, modo=modo))
    df[col_texto] = df[col_texto].apply(normalizar_espacios)

    # --- Paso 6: emojis ---
    print("\n[6/8] Procesando emojis...")
    df[col_texto] = df[col_texto].apply(lambda x: procesar_emojis(x, modo=modo))

    # --- Paso 7: ruido estructural ---
    print("\n[7/8] Limpiando ruido estructural (URLs, teléfonos, números, nombres)...")
    df = limpiar_ruido_estructural(
        df, col=col_texto, modo=modo,
        anonimizar=anonimizar, nombres=nombres,
        min_palabras=min_palabras,
    )

    # --- Paso 8: control de longitud ---
    print("\n[8/8] Gestionando longitudes de texto...")
    df = manejar_longitudes(
        df, col=col_texto,
        min_tokens=min_tokens, max_tokens=max_tokens,
        n_head=n_head_tokens, ruta_auditoria=ruta_auditoria,
    )

    # Eliminar filas con texto vacío residual
    df[col_texto] = df[col_texto].replace("", pd.NA)
    df = df.dropna(subset=[col_texto]).reset_index(drop=True)

    print(f"\n{'='*55}")
    print(f"  PIPELINE COMPLETADO  |  {len(df)} filas de salida")
    print(f"{'='*55}\n")

    return df


# ---------------------------------------------------------------------------
# Entrada por línea de comandos (opcional)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline de limpieza de reviews de hoteles.")
    parser.add_argument("--input",  required=True,  help="Ruta del CSV de entrada.")
    parser.add_argument("--output", required=True,  help="Ruta del CSV de salida.")
    parser.add_argument("--col_texto",    default="review",      help="Columna de texto.")
    parser.add_argument("--col_etiqueta", default="sentimiento", help="Columna de etiqueta.")
    parser.add_argument("--modo",         default="bert",        choices=["bert", "clasico"])
    parser.add_argument("--no_nombres",   action="store_true",   help="Desactiva la anonimización de nombres.")
    args = parser.parse_args()

    encoding = detectar_encoding(args.input)
    df_raw = pd.read_csv(args.input, encoding=encoding)
    print(f"Dataset cargado: {len(df_raw)} filas, columnas: {list(df_raw.columns)}")

    df_clean = run_pipeline(
        df_raw,
        col_texto=args.col_texto,
        col_etiqueta=args.col_etiqueta,
        modo=args.modo,
        nombres=not args.no_nombres,
    )

    df_clean.to_csv(args.output, index=False, encoding="utf-8")
    print(f"Dataset limpio guardado en: {args.output}")
