-- Migración: softmax por clase en predicciones_sentimiento
-- Añade prob_negativo, prob_neutro, prob_positivo (NULL en filas existentes hasta re-predicción).
--
-- Ejecutar antes de desplegar SentimentPrediction que inserta las tres columnas.

BEGIN;

ALTER TABLE predicciones_sentimiento
  ADD COLUMN IF NOT EXISTS prob_negativo NUMERIC(4,3)
    CHECK (prob_negativo IS NULL OR prob_negativo BETWEEN 0 AND 1),
  ADD COLUMN IF NOT EXISTS prob_neutro NUMERIC(4,3)
    CHECK (prob_neutro IS NULL OR prob_neutro BETWEEN 0 AND 1),
  ADD COLUMN IF NOT EXISTS prob_positivo NUMERIC(4,3)
    CHECK (prob_positivo IS NULL OR prob_positivo BETWEEN 0 AND 1);

COMMENT ON COLUMN predicciones_sentimiento.prob_negativo IS 'Probabilidad softmax clase negativa (0–1); NULL si fila anterior a esta migración.';
COMMENT ON COLUMN predicciones_sentimiento.prob_neutro IS 'Probabilidad softmax clase neutra (0–1); NULL si fila anterior a esta migración.';
COMMENT ON COLUMN predicciones_sentimiento.prob_positivo IS 'Probabilidad softmax clase positiva (0–1); NULL si fila anterior a esta migración.';

COMMIT;
