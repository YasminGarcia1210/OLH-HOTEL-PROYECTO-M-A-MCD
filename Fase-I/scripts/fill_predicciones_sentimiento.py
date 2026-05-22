"""
Lee todas las filas de `reviews`, clasifica sentimiento con Robertuito
(`pysentimiento/robertuito-sentiment-analysis`) e inserta en `predicciones_sentimiento`.

Requisitos: DATABASE_URL (PostgreSQL), torch, transformers, psycopg2-binary.

Nota: el checkpoint en `sources/sentimentAnalysis/p91` usa nombres de capas
incompatibles con `AutoModelForSequenceClassification`; se usa el modelo
oficial del Hub para inferencia correcta.
"""
from __future__ import annotations

import os
import sys

import psycopg2
from psycopg2.extras import execute_values
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_ID = "pysentimiento/robertuito-sentiment-analysis"
MODEL_VERSION = "pysentimiento/robertuito-sentiment-analysis"
BATCH_SIZE = 8

# El Hub usa NEG/NEU/POS; la BD exige negativo/neutro/positivo (ddl_bd.sql).
_LABEL_TO_BD = {
    "NEG": "negativo",
    "NEU": "neutro",
    "POS": "positivo",
    "negativo": "negativo",
    "neutro": "neutro",
    "positivo": "positivo",
}


def _sentimiento_bd(raw: str) -> str:
    key = (raw or "").strip()
    if key in _LABEL_TO_BD:
        return _LABEL_TO_BD[key]
    low = key.lower()
    if low in ("neg", "negative"):
        return "negativo"
    if low in ("neu", "neutral"):
        return "neutro"
    if low in ("pos", "positive"):
        return "positivo"
    raise ValueError(f"Etiqueta de sentimiento no reconocida: {raw!r}")


def _probs_por_clase_bd(id2label, probs_row) -> dict[str, float]:
    """Acumula softmax por etiqueta canónica negativo / neutro / positivo."""
    acum = {"negativo": 0.0, "neutro": 0.0, "positivo": 0.0}
    for j in range(int(probs_row.shape[0])):
        raw = id2label.get(j) if isinstance(id2label, dict) else None
        if raw is None and isinstance(id2label, dict):
            raw = id2label.get(str(j))
        key = _sentimiento_bd(str(raw)) if raw is not None else "neutro"
        acum[key] += float(probs_row[j].item())
    return acum


def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
    model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    return tokenizer, model


@torch.inference_mode()
def predict_batch(
    tokenizer,
    model,
    texts: list[str],
) -> list[tuple[str, float, dict[str, float]]]:
    device = next(model.parameters()).device
    enc = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    enc = {k: v.to(device) for k, v in enc.items()}
    logits = model(**enc).logits
    probs = torch.softmax(logits, dim=-1)
    conf, pred_ids = probs.max(dim=-1)
    id2label = model.config.id2label
    out = []
    for i in range(len(texts)):
        pred_idx = int(pred_ids[i].item())
        raw = id2label.get(pred_idx) if isinstance(id2label, dict) else None
        if raw is None and isinstance(id2label, dict):
            raw = id2label.get(str(pred_idx))
        label = _sentimiento_bd(str(raw)) if raw is not None else "neutro"
        c = float(conf[i].item())
        pmap = _probs_por_clase_bd(id2label, probs[i])
        out.append((label, c, pmap))
    return out


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Defina DATABASE_URL con la cadena de conexión PostgreSQL.", file=sys.stderr)
        sys.exit(1)

    tokenizer, model = load_model()

    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, texto_limpio
                FROM reviews
                ORDER BY id
                """
            )
            rows = cur.fetchall()

        if not rows:
            print("No hay reviews en la tabla.")
            return

        predictions: list[tuple[int, str, float, float, float, float, str]] = []
        for start in range(0, len(rows), BATCH_SIZE):
            chunk = rows[start : start + BATCH_SIZE]
            ids = [r[0] for r in chunk]
            texts = [r[1] or "" for r in chunk]
            batch_pred = predict_batch(tokenizer, model, texts)
            for rid, (sent, conf, pmap) in zip(ids, batch_pred):
                predictions.append(
                    (
                        rid,
                        sent,
                        round(conf, 3),
                        round(pmap["negativo"], 3),
                        round(pmap["neutro"], 3),
                        round(pmap["positivo"], 3),
                        MODEL_VERSION,
                    )
                )

        sql = """
            INSERT INTO predicciones_sentimiento (
                review_id, sentimiento, confianza,
                prob_negativo, prob_neutro, prob_positivo,
                modelo_version
            )
            VALUES %s
            ON CONFLICT (review_id) DO UPDATE SET
                sentimiento = EXCLUDED.sentimiento,
                confianza = EXCLUDED.confianza,
                prob_negativo = EXCLUDED.prob_negativo,
                prob_neutro = EXCLUDED.prob_neutro,
                prob_positivo = EXCLUDED.prob_positivo,
                modelo_version = EXCLUDED.modelo_version,
                procesado_en = NOW()
        """
        with conn.cursor() as cur:
            execute_values(cur, sql, predictions)
        conn.commit()
        print(f"Insertadas/actualizadas {len(predictions)} predicciones.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
