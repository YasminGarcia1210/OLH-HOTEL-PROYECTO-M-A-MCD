# Clasificación de sentimiento en español (3 clases)

Modelo para clasificar texto en **negativo**, **neutro** y **positivo** (español).

## Base y tarea

- **Arquitectura:** `RobertaForSequenceClassification` (12 capas, 768 dimensiones ocultas, 12 cabezas de atención), familia RoBERTa.
- **Punto de partida:** [`pysentimiento/robertuito-sentiment-analysis`](https://huggingface.co/pysentimiento/robertuito-sentiment-analysis) (Robertuito, orientado a español y variantes de Twitter).
- **Tarea:** clasificación multiclase de una etiqueta (`single_label_classification`).
- **Salida:** 3 logits; el orden de las clases coincide con `id2label` en `config.json`.

## Etiquetas

| ID | Etiqueta   |
|----|------------|
| 0  | negativo   |
| 1  | neutro     |
| 2  | positivo   |

La correspondencia también está en `label_mapping.json` y en `config.json` (`id2label` / `label2id`).

## Artefactos del repositorio

| Archivo                 | Descripción |
|-------------------------|-------------|
| `model.safetensors`     | Pesos del modelo (encoder y cabezal de clasificación). |
| `config.json`           | Hiperparámetros (`model_type: roberta`), vocabulario, mapeo de etiquetas. |
| `tokenizer_config.json` | Configuración del tokenizador (p. ej. longitud máxima 128, tokens especiales RoBERTa). |
| `label_mapping.json`    | Mapeo explícito id ↔ etiqueta. |
| `results.md`            | Informe de evaluación del split usado al exportar el modelo. |

## Tokenización

- **Longitud máxima típica:** 128 tokens (ver `tokenizer_config.json`).
- Textos más largos se truncan por la derecha (`truncation_side: right`).

## Rendimiento reportado

Sobre **1462** muestras de evaluación (detalle en `results.md`):

- **Accuracy:** 0.89  
- **F1 (macro / ponderado):** ~0.89  
- **F1 por clase:** negativo ~0.87, neutro ~0.88, positivo ~0.91  

Estas métricas corresponden a ese conjunto concreto; conviene reevaluar en datos de tu dominio.

## Carga con `transformers`

Ejemplo estándar (ajusta la ruta o el identificador del modelo en el Hub según publiques el repositorio):

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer

model = AutoModelForSequenceClassification.from_pretrained(".")  # o tu repo_id
tokenizer = AutoTokenizer.from_pretrained(".")
```

Si tu integración carga el archivo de pesos a mano y falla el emparejamiento de claves respecto a `AutoModelForSequenceClassification`, puede deberse a prefijos distintos en el checkpoint (p. ej. `encoder.*` frente a `roberta.*`) o a un cabezal MLP personalizado; en ese caso revisa el mapeo de nombres de capas o usa la misma definición de cabezal con la que se entrenó el modelo.

## Referencias

- [Robertuito sentiment](https://huggingface.co/pysentimiento/robertuito-sentiment-analysis)
