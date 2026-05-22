# 🏨 Sistema Inteligente de Análisis de Sentimiento y Recomendaciones
**Optimización de Experiencia en el Sector Hotelero**

## 📌 Descripción del Proyecto

Este proyecto tiene como objetivo transformar la gestión operativa y estratégica del hotel mediante la automatización de indicadores clave (KPIs), análisis de emociones en reseñas y mensajes de clientes, y la implementación de un sistema recomendador inteligente.

La iniciativa evoluciona en tres fases:

- 🔵 [Inteligencia Interna](Fase-I/) — implementada en [`Fase-I/`](Fase-I/)
- 🟣 Sistema Recomendador
- 🟢 Agente Inteligente de Reservas

El enfoque es escalable, de bajo costo y orientado a impacto real en reputación, ingresos y experiencia del huésped.

## 📁 Estructura del repositorio

| Ruta | Contenido |
|------|-----------|
| **[`Fase-I/`](Fase-I/)** | Implementación de **Fase 1 – Inteligencia interna**: microservicios, dashboard, notebooks, contratos API y documentación técnica. Ver [`Fase-I/README.md`](Fase-I/README.md). |
| `docs/` | Guías transversales del repositorio (p. ej. instalación). |
| `notebooks/` | Notebooks en la raíz del monorepo (complementarios al trabajo en `Fase-I/notebooks/`). |
| `src/` · `tests/` | Esqueleto de experimentación / entrenamiento de modelos en la raíz. |

> La documentación operativa, el pipeline de microservicios, el DDL, OpenAPI y los README por servicio viven bajo **`Fase-I/`**.

## 🟡 Fase 0 – Automatización Operativa (Transversal)

Esta etapa acompaña todo el proyecto y habilita automatizaciones desde la reserva hasta la atención post‑estadía, incluyendo un agente ligero conectado a WhatsApp Business.

### Alcance

- Captura y normalización de solicitudes de reserva.
- Respuestas automáticas iniciales y recolección de datos básicos.
- Confirmación y actualización de reservas.
- Derivación a humano ante casos complejos.

### Flujo operativo (Fase 0)

```mermaid
flowchart TD
    A[Cliente / OTA / WhatsApp] --> B[Webhook o API de mensajería]
    B --> C[Orquestador ligero<br/>reglas + plantillas]
    C --> D[Verificación de disponibilidad<br/>PMS / inventario]
    D --> E[Propuesta de reserva + confirmación]
    E --> F[Registro en base + notificaciones internas]
    F --> G[Seguimiento automático<br/>pre-check-in y post-estadía]
    C --> H[Derivación a humano<br/>casos complejos]

    classDef fase0 fill:#FDE68A,stroke:#B45309,stroke-width:1px,color:#1F2937;
    class A,B,C,D,E,F,G,H fase0;
```

## 🎯 Objetivos Estratégicos

- Automatizar el análisis de reseñas y mensajes.
- Medir en tiempo real indicadores de reputación.
- Detectar alertas tempranas de posibles crisis.
- Personalizar la oferta de servicios.
- Evolucionar hacia un agente autónomo de reservas.

## 🏗 Arquitectura General

Plataformas (Google, Booking, Airbnb)

WhatsApp Business
↓
Pipeline de datos (Python + NLP)
↓
Base estructurada
↓
Dashboard ejecutivo + Sistema de alertas
↓
Motor de recomendación
↓
Agente inteligente (Fase 3)

## 🔵 Fase 1 – Inteligencia Interna

**Código y documentación:** [`Fase-I/`](Fase-I/) · guía completa en [`Fase-I/README.md`](Fase-I/README.md)

### Alcance

- Consolidación automática de datos.
- Análisis de sentimiento y emociones.
- Identificación de tópicos críticos (ABSA).
- Automatización de KPIs.
- Dashboard ejecutivo.
- Sistema de alertas tempranas.
- MLOps y despliegue en contenedores (Azure Container Apps, según servicio).

### Implementación actual (`Fase-I/`)

Pipeline de microservicios (Python/Flask) orquestado sobre PostgreSQL y Azure Blob Storage:

1. **Data Verification & Cleaner** — ingesta, validación y limpieza de CSV de reseñas.
2. **Sentiment Prediction** — inferencia de sentimiento (modelo BERT).
3. **ABSAService** — análisis por aspectos / tópicos hacia `review_topicos`.
4. **MetricProcessor** — cálculo batch de KPIs agregados.
5. **Dashboard Backend** — API de lectura para el front.
6. **olh-sentiment-ia** — dashboard y administración (Next.js).

Artefactos adicionales: `guidelines/` (contratos REST, DDL, migraciones), `notebooks/` (EDA, ABSA, experimentos), `pipeline/` (diagrama interactivo del flujo), `Poc/` (POC estática de referencia).

### KPIs Clave

- Rating promedio.
- Evolución del sentimiento.
- Tiempo de respuesta.
- Índice de Experiencia Inteligente (IEI).
- Sentimiento por tópico y alertas por umbral (detalle en `Fase-I/guidelines/`).

## 🟣 Fase 2 – Sistema Recomendador

### Alcance

- Segmentación automática de huéspedes.
- Motor de reglas de recomendación.
- Personalización de ofertas.
- Integración con comunicación (WhatsApp).
- Medición de aceptación y conversión.

### Métricas

- CTR de recomendaciones.
- Tasa de conversión.
- Incremento en ventas cruzadas.
- Recompra.

## 🟢 Fase 3 – Agente Inteligente de Reservas

### Alcance

- Gestión automática de reservas.
- Respuestas inteligentes en WhatsApp.
- Detección de intención.
- Sugerencias personalizadas en tiempo real.
- Integración con sistema actual del hotel.

## 📊 Entregables

- Base de datos consolidada.
- Motor NLP operativo.
- Dashboard gerencial.
- Sistema de alertas.
- Recomendador funcional.
- Roadmap evolutivo.
- Documento técnico final.

## 💻 Tecnologías

**Fase 1 (en [`Fase-I/`](Fase-I/)):** Python · Flask · PostgreSQL (p. ej. Neon) · Transformers/BERT · Next.js · Azure Blob Storage · Docker / Azure Container Apps · notebooks de experimentación.

**Fases posteriores y transversales:** WhatsApp Business API · motor de recomendación · agente de reservas · visualización ejecutiva (Power BI o Looker Studio, según evolución del proyecto).

## 📅 Cronograma

- Inicio: 16 febrero
- Horizonte: 16 semanas (febrero–junio)
- Finalización Fase 2: primera semana de junio
- Fase 3: evolutiva posterior (arranca en S13)

### Metodología Gantt (semanas S1–S16)

**Leyenda:** 🟨 Fase 0 · 🟦 Fase 1 · 🟪 Fase 2 · 🟩 Fase 3 · — sin actividad

| Actividad | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | S11 | S12 | S13 | S14 | S15 | S16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fase 0 – Automatización operativa | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 |
| Levantamiento + KPIs | 🟦 | 🟦 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Pipeline de datos | — | — | 🟦 | 🟦 | — | — | — | — | — | — | — | — | — | — | — | — |
| Análisis emocional | — | — | — | — | 🟦 | 🟦 | — | — | — | — | — | — | — | — | — | — |
| Alertas automáticas | — | — | — | — | — | — | 🟦 | — | — | — | — | — | — | — | — | — |
| Dashboard ejecutivo | — | — | — | — | — | — | — | 🟦 | — | — | — | — | — | — | — | — |
| Segmentación clientes | — | — | — | — | — | — | — | — | 🟪 | 🟪 | — | — | — | — | — | — |
| Motor recomendación | — | — | — | — | — | — | — | — | — | — | 🟪 | 🟪 | — | — | — | — |
| Integración comunicación | — | — | — | — | — | — | — | — | — | — | — | — | 🟪 | 🟪 | — | — |
| Métricas impacto | — | — | — | — | — | — | — | — | — | — | — | — | — | — | 🟪 | — |
| Diseño agente reservas | — | — | — | — | — | — | — | — | — | — | — | — | 🟩 | 🟩 | — | — |
| Integración WhatsApp IA | — | — | — | — | — | — | — | — | — | — | — | — | — | 🟩 | 🟩 | — |
| Pruebas piloto agente | — | — | — | — | — | — | — | — | — | — | — | — | — | — | 🟩 | — |
| Presentación final | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | 🟩 |

## 🚀 Impacto Esperado

- Mejora reputacional medible.
- Reducción de crisis.
- Toma de decisiones basada en datos.
- Personalización real del servicio.
- Base para transformación digital hotelera.

## 🧠 Visión

Evolucionar hacia un modelo de hotel inteligente donde la experiencia del huésped, la reputación y la operación estén conectadas mediante inteligencia artificial.

---

## ✨ Firma Estratégica

Proyecto diseñado para escalar de analítica operativa a inteligencia accionable, con foco en reputación, ingresos y experiencia del huésped.
