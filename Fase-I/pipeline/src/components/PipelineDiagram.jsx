import { useState } from "react";

const pipeline = [
  {
    phase: "1. Recolección e ingesta",
    color: "#0EA5E9",
    icon: "🌐",
    steps: [
      { id: "1.1", label: "TripAdvisor", detail: "Fuente: comentarios y reseñas de lugares turísticos (scraping o export)" },
      { id: "1.2", label: "Booking", detail: "Fuente: reseñas de alojamientos y valoraciones de usuarios" },
      { id: "1.3", label: "Ingesta en lotes", detail: "Datos que llegan en volúmenes grandes (batches); procesamiento por lotes" },
      { id: "1.4", label: "Google Drive", detail: "Subida de archivos (CSV/JSON) y lectura desde Drive (API o enlace compartido)" },
      { id: "1.5", label: "Dataset crudo unificado", detail: "Campos unificados: usuario, fecha, título, texto, rating, fuente (TripAdvisor/Booking)" },
      { id: "1.6", label: "Validación de calidad y esquema", detail: "Completitud, duplicados, rangos de rating; validación de esquema por lote" },
      { id: "1.7", label: "Versionado de datos", detail: "Catálogo o versionado (ej. DVC) para trazabilidad: qué datos entrenó cada modelo" },
    ],
  },
  {
    phase: "2. Limpieza",
    color: "#8B5CF6",
    icon: "🧹",
    steps: [
      { id: "2.1", label: "Eliminar HTML", detail: "Quitar etiquetas <br />, <p>, etc." },
      { id: "2.2", label: "Normalización", detail: "Símbolos extraños, espacios; para BERT/BETO se preserva contexto" },
      { id: "2.3", label: "Unificación de ratings", detail: "Mapear escalas TripAdvisor/Booking a 1–5 estrellas cuando aplique" },
    ],
  },
  {
    phase: "3. Etiquetado (5 clases)",
    color: "#F59E0B",
    icon: "🏷️",
    steps: [
      { id: "3.1", label: "1 estrella → Muy negativo", detail: "Sentimiento muy negativo" },
      { id: "3.2", label: "2 estrellas → Negativo", detail: "Sentimiento negativo" },
      { id: "3.3", label: "3 estrellas → Neutral", detail: "Sentimiento neutral" },
      { id: "3.4", label: "4 estrellas → Positivo", detail: "Sentimiento positivo" },
      { id: "3.5", label: "5 estrellas → Muy positivo", detail: "Sentimiento muy positivo" },
    ],
  },
  {
    phase: "4. Transformación",
    color: "#10B981",
    icon: "⚙️",
    steps: [
      { id: "4.1", label: "Train / Val / Test Split", detail: "Partición para entrenamiento, validación y prueba" },
      { id: "4.2", label: "Tokenización (BETO/GPT)", detail: "Subword tokenization, vocabulario del modelo, max length" },
      { id: "4.3", label: "Input para transformers", detail: "Input IDs, attention mask; opcional baseline BoW/TF-IDF" },
      { id: "4.4", label: "Desbalance de clases (opcional)", detail: "Estrategias si hay desbalance: ponderación, oversampling o evaluación con F1 macro" },
    ],
  },
  {
    phase: "5. Modelos de clasificación",
    color: "#EF4444",
    icon: "🤖",
    steps: [
      { id: "5.1", label: "BETO (BERT español) preentrenado", detail: "Modelo principal: fine-tuning para 5 clases de sentimiento" },
      { id: "5.2", label: "GPT / modelos generativos", detail: "Uso de modelos tipo GPT para clasificación o generación de etiquetas" },
      { id: "5.3", label: "Otras redes Transformer", detail: "Comparativa con otros transformers (multiclase, 5 clases)" },
      { id: "5.4", label: "Experiment tracking", detail: "Registro de hiperparámetros, métricas y artefactos (MLflow, W&B u otro)" },
      { id: "5.5", label: "Reproducibilidad", detail: "Seeds fijos, configs versionadas, entorno documentado para repetir experimentos" },
    ],
  },
  {
    phase: "6. Validación",
    color: "#6366F1",
    icon: "✅",
    steps: [
      { id: "6.1", label: "Métricas multiclase", detail: "Precision, Recall, F1-score (macro/micro), Accuracy, matriz de confusión" },
      { id: "6.2", label: "Validación cruzada", detail: "Estimación de precisión y variación entre folds" },
    ],
  },
  {
    phase: "7. ABSA (Análisis por aspectos)",
    color: "#EC4899",
    icon: "🎯",
    steps: [
      { id: "7.1", label: "Aspect-Based Sentiment Analysis", detail: "Sentimiento asociado a aspectos concretos del texto" },
      { id: "7.2", label: "Identificación de tópicos/aspectos", detail: "Ej.: Aseo, Atención al cliente, Ruido, Ubicación, Precio, Comodidad" },
      { id: "7.3", label: "Sentimiento por aspecto", detail: "Clasificación 5 clases por cada tópico identificado en la reseña" },
    ],
  },
  {
    phase: "8. Comparación y registro",
    color: "#14B8A6",
    icon: "📦",
    steps: [
      { id: "8.1", label: "Comparación de resultados", detail: "Evaluar métricas de todos los modelos (BETO, GPT, otros transformers)" },
      { id: "8.2", label: "Selección del mejor modelo", detail: "Criterios: F1, accuracy, robustez; se elige el modelo óptimo" },
      { id: "8.3", label: "Despliegue en Model Registry", detail: "Registrar y versionar el modelo elegido para uso en producción" },
    ],
  },
  {
    phase: "9. Monitoreo y ciclo de vida",
    color: "#F97316",
    icon: "🔄",
    steps: [
      { id: "9.1", label: "Serving / API", detail: "Exponer el modelo registrado como API o servicio para inferencia" },
      { id: "9.2", label: "Monitoreo en producción", detail: "Rendimiento, latencia; detección de data drift y concept drift" },
      { id: "9.3", label: "Reentrenamiento y feedback", detail: "Disparadores para reentrenar; incorporar feedback o nuevos datos al pipeline" },
    ],
  },
];

export default function PipelineDiagram() {
  const [active, setActive] = useState(null);

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0f0f1a",
      fontFamily: "'Segoe UI', sans-serif",
      padding: "2rem",
      color: "#e2e8f0",
    }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <h1 style={{
          textAlign: "center",
          fontSize: "1.5rem",
          fontWeight: 700,
          letterSpacing: "0.05em",
          color: "#f8fafc",
          marginBottom: "0.25rem",
        }}>
          Pipeline de Análisis de Sentimiento y ABSA
        </h1>
        <p style={{ textAlign: "center", color: "#94a3b8", fontSize: "0.85rem", marginBottom: "2.5rem" }}>
          5 clases (1–5 estrellas) · BETO + Transformers · ABSA por tópicos · TripAdvisor y Booking
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
          {pipeline.map((phase, pi) => (
            <div key={pi}>
              {/* Phase Header */}
              <button
                onClick={() => setActive(active === pi ? null : pi)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  background: active === pi
                    ? `${phase.color}22`
                    : "rgba(255,255,255,0.04)",
                  border: `1.5px solid ${active === pi ? phase.color : "rgba(255,255,255,0.08)"}`,
                  borderRadius: "10px",
                  padding: "0.75rem 1.2rem",
                  cursor: "pointer",
                  color: "#f1f5f9",
                  textAlign: "left",
                  transition: "all 0.2s",
                }}
              >
                <span style={{
                  fontSize: "1.4rem",
                  width: 32,
                  textAlign: "center",
                  filter: active === pi ? "none" : "grayscale(0.3)",
                }}>{phase.icon}</span>
                <span style={{
                  fontWeight: 600,
                  fontSize: "0.95rem",
                  color: active === pi ? phase.color : "#cbd5e1",
                  flex: 1,
                }}>{phase.phase}</span>
                <span style={{
                  fontSize: "0.75rem",
                  color: "#64748b",
                  background: "rgba(255,255,255,0.05)",
                  borderRadius: 6,
                  padding: "2px 8px",
                }}>{phase.steps.length} paso{phase.steps.length > 1 ? "s" : ""}</span>
                <span style={{
                  color: active === pi ? phase.color : "#475569",
                  fontSize: "1rem",
                  transition: "transform 0.2s",
                  transform: active === pi ? "rotate(90deg)" : "none",
                }}>▶</span>
              </button>

              {/* Steps */}
              {active === pi && (
                <div style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "0.6rem",
                  padding: "0.75rem 1rem",
                  background: `${phase.color}09`,
                  borderLeft: `3px solid ${phase.color}`,
                  borderRadius: "0 0 10px 10px",
                  marginTop: "-4px",
                }}>
                  {phase.steps.map((step, si) => (
                    <div key={si} style={{
                      background: `${phase.color}18`,
                      border: `1px solid ${phase.color}44`,
                      borderRadius: 8,
                      padding: "0.6rem 1rem",
                      minWidth: 200,
                      flex: "1 1 200px",
                    }}>
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        marginBottom: "0.25rem",
                      }}>
                        <span style={{
                          background: phase.color,
                          color: "#fff",
                          fontSize: "0.65rem",
                          fontWeight: 700,
                          borderRadius: 4,
                          padding: "1px 6px",
                        }}>{step.id}</span>
                        <span style={{
                          fontWeight: 600,
                          fontSize: "0.85rem",
                          color: "#f1f5f9",
                        }}>{step.label}</span>
                      </div>
                      <p style={{
                        margin: 0,
                        fontSize: "0.75rem",
                        color: "#94a3b8",
                        lineHeight: 1.4,
                      }}>{step.detail}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Connector */}
              {pi < pipeline.length - 1 && (
                <div style={{
                  display: "flex",
                  justifyContent: "center",
                  margin: "0.1rem 0",
                  color: "#334155",
                  fontSize: "1.1rem",
                }}>↓</div>
              )}
            </div>
          ))}
        </div>

        {/* Result summary */}
        <div style={{
          marginTop: "2rem",
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "0.75rem",
        }}>
          {[
            { label: "Clasificación", value: "5 clases", color: "#F59E0B", detail: "Muy neg → Muy pos (1–5 ★)" },
            { label: "Modelo principal", value: "BETO", color: "#EF4444", detail: "BERT español fine-tuned" },
            { label: "Objetivo final", value: "Registry", color: "#14B8A6", detail: "Comparar → elegir mejor → desplegar" },
          ].map((r, i) => (
            <div key={i} style={{
              background: `${r.color}15`,
              border: `1px solid ${r.color}44`,
              borderRadius: 10,
              padding: "1rem",
              textAlign: "center",
            }}>
              <div style={{ fontSize: "1.25rem", fontWeight: 800, color: r.color }}>{r.value}</div>
              <div style={{ fontSize: "0.8rem", color: "#f1f5f9", marginTop: 2 }}>{r.label}</div>
              <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: 4 }}>{r.detail}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
