# Pipeline de Análisis de Sentimiento y ABSA

Diagrama interactivo del **pipeline de datos para IA** del proyecto de tesis: clasificación de sentimiento en comentarios turísticos, análisis por aspectos (ABSA) y despliegue del mejor modelo en un registry.

## Resumen del pipeline

| Fase | Descripción |
|------|-------------|
| **1. Recolección e ingesta** | Fuentes TripAdvisor y Booking; datos en lotes grandes; almacenamiento y lectura desde Google Drive; validación de calidad/esquema; versionado de datos (trazabilidad). |
| **2. Limpieza** | Eliminación de HTML, normalización, unificación de ratings a escala 1–5 estrellas. |
| **3. Etiquetado (5 clases)** | Muy negativo (1★), Negativo (2★), Neutral (3★), Positivo (4★), Muy positivo (5★). |
| **4. Transformación** | Train/val/test split; tokenización para BETO/GPT; preparación de inputs para transformers; manejo opcional de desbalance de clases. |
| **5. Modelos de clasificación** | BETO (BERT español) preentrenado y fine-tuned; GPT y otros transformers; experiment tracking y reproducibilidad. |
| **6. Validación** | Métricas multiclase (Precision, Recall, F1, Accuracy), validación cruzada. |
| **7. ABSA** | Análisis de sentimiento por aspectos; identificación de tópicos (Aseo, Atención al cliente, Ruido, Ubicación, etc.); sentimiento 5 clases por aspecto. |
| **8. Comparación y registro** | Comparación de resultados entre modelos; selección del mejor; despliegue en **Model Registry** (versionado para producción). |
| **9. Monitoreo y ciclo de vida** | Serving/API del modelo; monitoreo en producción (drift, rendimiento); reentrenamiento y feedback. |

## Tecnologías y enfoque

- **Datos:** TripAdvisor, Booking; ingesta por lotes; Google Drive; versionado de datasets.
- **Clasificación:** 5 clases de sentimiento (1–5 estrellas).
- **Modelos:** BETO (principal), GPT y otras redes Transformer; experiment tracking (ej. MLflow, W&B); reproducibilidad.
- **ABSA:** Tópicos/aspectos (aseo, atención, ruido, ubicación, precio, comodidad, etc.) con sentimiento por aspecto.
- **Operación:** Comparar modelos → elegir el mejor → registrar en Model Registry → serving, monitoreo y reentrenamiento.

## Ejecutar en desarrollo

```bash
cd Tesis/pipeline
npm install
npm run dev
```

Abre la URL que muestra la terminal (por ejemplo `http://localhost:5173`).

## Build para producción

```bash
npm run build
npm run preview
```

Los archivos generados quedan en `dist/`.
