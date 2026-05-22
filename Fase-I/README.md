# Sistema Inteligente de Análisis de Sentimiento y Recomendaciones
## Optimización de Experiencia en el Sector Hotelero

Proyecto de tesis orientado a transformar la gestión operativa y estratégica del hotel mediante la automatización de indicadores clave (KPIs), análisis de sentimiento en reseñas, ABSA (sentimiento por aspectos / tópicos) y un dashboard ejecutivo conectado a APIs dedicadas.

---

## Descripción del proyecto

La iniciativa evoluciona en **tres fases** principales, con una fase transversal de automatización:

| Fase | Nombre | Enfoque |
|------|--------|---------|
| **Fase 1** | Inteligencia interna | Ingesta y limpieza, sentimiento, tópicos (ABSA), métricas, backend de lecturas y aplicación web |
| **Fase 2** | Sistema recomendador | Segmentación, motor de recomendaciones, personalización e integración con comunicación |
| **Fase 3** | Agente inteligente de reservas | Gestión automática de reservas, respuestas en canales tipo WhatsApp, detección de intención |

---

## Fase 1 – Arquitectura actual

### Flujo de microservicios (pipeline)

Orquestación típica (scheduler u otro disparador) según [`guidelines/api-contracts.md`](guidelines/api-contracts.md):

```
Azure Blob Storage (CSV de entrada)
        ↓
┌─────────────────────────────────────┐
│  Data Verification & Cleaner        │  Valida, limpia, inserta `reviews` + `log_archivos`
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  Sentiment Prediction               │  Predice sentimiento (modelo BERT en servicio)
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  ABSAService                         │  ABSA / tópicos → `review_topicos` (LLM u OpenAI Batch)
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  MetricProcessor                     │  `POST /metricas/calcular` — KPIs agregados en BD
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  Dashboard Backend                  │  Lecturas: KPIs, series, tópicos, alertas, reviews, blobs
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  olh-sentiment-ia (Next.js)        │  Dashboard y administración de archivos de entrada
└─────────────────────────────────────┘
```

Cada servicio tiene su propio `README.md` bajo `sources/apis/<nombre>/`.

### Servicios en el repositorio

| Componente | Rol | Documentación |
|------------|-----|----------------|
| **Data Verification & Cleaner** | Ingesta desde blob, validación, limpieza, persistencia; despliegue opcional en Azure Container Apps | [`sources/apis/DataVerificationCleanner/README.md`](sources/apis/DataVerificationCleanner/README.md) |
| **Sentiment Prediction** | Inferencia de sentimiento por review | [`sources/apis/SentimentPrediction/README.md`](sources/apis/SentimentPrediction/README.md) |
| **ABSAService** | Análisis por aspectos / tópicos hacia `review_topicos` | [`sources/apis/ABSAService/README.md`](sources/apis/ABSAService/README.md) |
| **MetricProcessor** | Cálculo batch de métricas (`POST /metricas/calcular`) | [`sources/apis/MetricProcessor/README.md`](sources/apis/MetricProcessor/README.md) |
| **Dashboard Backend** | API de lectura para el front (misma convención de ruta `/api/v1/metricas` en otro proceso) | [`sources/apis/DashboardBackend/README.md`](sources/apis/DashboardBackend/README.md) |
| **olh-sentiment-ia** | Front Next.js (dashboard, reviews, admin) | [`sources/app/olh-sentiment-ia/README.md`](sources/app/olh-sentiment-ia/README.md) |

**Otros artefactos de Fase 1**

- **`Poc/`** — SPA estática inicial (HTML/JS/Chart.js); referencia histórica o demos ligeras.
- **`pipeline/`** — Aplicación Vite con diagrama interactivo del pipeline de datos e IA; ver [`pipeline/README.md`](pipeline/README.md).
- **`sources/libs/metricas_read/`** — Paquete Python compartido para lectura/agregación de métricas; ver su README.
- **`sources/sentimentAnalysis/`** — Artefactos y configuración de experimentos de modelos de sentimiento.

---

## Pipeline de datos (resumen – Data Verification & Cleaner)

Al procesar un archivo de entrada:

```
1. Descarga el CSV desde Azure Blob Storage (ruta en contenedor configurado)
2. Valida columnas requeridas (review, fecha) y formato ISO en fechas
3. Ejecuta pipeline de limpieza de texto (encoding, idioma, HTML, emojis, anonimización, longitud)
4. INSERT atómico: log_archivos + reviews en PostgreSQL
5. Opcional: sube CSV limpio y mueve el origen a prefijo procesado (según configuración)
```

Detalle operativo y variables: README del servicio y `guidelines/api-contracts.md`.

---

## Estructura del repositorio

```
Tesis/
├── README.md                          # Este archivo
├── docs/                              # Documentación académica / entregables (p. ej. trabajo final)
├── guidelines/                        # Contratos, DDL, migraciones, guías de KPIs y desarrollo local
│   ├── api-contracts.md                 # Contratos REST entre servicios y orden del pipeline
│   ├── ddl_bd.sql                     # DDL PostgreSQL
│   ├── openapi.json                   # OpenAPI 3.0
│   ├── er-diagram.puml                # Diagrama ER (PlantUML)
│   ├── calculo-metricas.md            # Reglas de métricas
│   ├── Guia_KPIs_Hoteles_OLH.md
│   ├── Desarrollo_Local.md
│   ├── flask-apis/                    # Guías para APIs Flask
│   ├── hoteles_*.sql, topicos_*.sql   # Datos semilla
│   └── migracion_*.sql                # Scripts de migración incremental
│
├── pipeline/                          # Diagrama interactivo del pipeline (npm / Vite)
├── Poc/                               # POC dashboard estático
├── notebooks/                         # EDA, limpieza, sentimiento, ABSA, Ollama/OpenAI
│   ├── EDA/
│   └── ABSA/
│
└── sources/
    ├── app/
    │   └── olh-sentiment-ia/          # Dashboard Next.js
    ├── apis/
    │   ├── DataVerificationCleanner/  # Ingesta y limpieza (+ deploy Azure ACA en docs/)
    │   ├── SentimentPrediction/
    │   ├── ABSAService/
    │   ├── MetricProcessor/
    │   └── DashboardBackend/
    ├── libs/
    │   └── metricas_read/             # Librería Python de métricas
    ├── sentimentAnalysis/             # Experimentos / modelos
    ├── scripts/                       # cleaning_pipeline.py y guía asociada
    └── data/                          # Datasets y archivos de prueba
```

---

## Base de datos

PostgreSQL (p. ej. **Neon** serverless en despliegues actuales). Tablas principales alineadas con el DDL en `guidelines/ddl_bd.sql`:

| Tabla | Descripción |
|-------|-------------|
| `hoteles` | Catálogo de hoteles |
| `topicos` | Tópicos monitoreados |
| `log_archivos` | Auditoría por archivo procesado (incluye hash del origen) |
| `reviews` | Reviews cargadas y limpias |
| `predicciones_sentimiento` | Sentimiento por review |
| `review_topicos` | Tópicos / aspectos por review (p. ej. vía ABSA) |
| `metricas_globales_mensual` | KPIs globales por mes |
| `metricas_topico_mensual` | KPIs por tópico por mes |
| `alertas` | Alertas por umbrales |

---

## Stack tecnológico (visión general)

| Área | Tecnología |
|------|------------|
| APIs | Python · Flask · REST · Gunicorn (contenedores) |
| Front | Next.js · TypeScript · React |
| NLP / ML | Transformers · BERT · notebooks de experimentación |
| ABSA | Servicio dedicado (LLM local u OpenAI Batch según configuración) |
| Datos | PostgreSQL · psycopg2 · Pandas · spaCy / utilidades de limpieza |
| Almacenamiento de archivos | Azure Blob Storage (ingesta y archivos de entrada para el dashboard) |
| Visualización adicional | Chart.js (`Poc/`) · diagrama en `pipeline/` (React/Vite) |
| Configuración | YAML · variables de entorno · python-dotenv |

---

## KPIs del dashboard

| KPI | Descripción |
|-----|-------------|
| Sentimiento promedio (%) | Porcentaje de reviews positivas en el período |
| Reviews analizadas | Total de reseñas procesadas |
| Tópicos con alerta | Tópicos por debajo del umbral |
| Sentimiento en el tiempo | Serie mensual filtrable |
| Score por tópico | Sentimiento por cada tópico monitoreado |
| Top 5 críticos | Tópicos con menor score |

### Tópicos monitoreados (referencia)

`Limpieza` · `Atención al cliente` · `Instalaciones y servicios` ·
`Relación calidad-precio` · `Ruido` · `WiFi` · `Comodidad` · `Desayuno / Gastronomía`

(La lista canónica en BD está en `guidelines/` y semillas `topicos_*.sql`.)

---

## Fases futuras

### Fase 2 – Sistema recomendador
- Segmentación automática de huéspedes
- Motor de recomendaciones personalizado
- Integración con WhatsApp Business

### Fase 3 – Agente inteligente de reservas
- Gestión automática de reservas
- Respuestas inteligentes en WhatsApp
- Detección de intención y sugerencias en tiempo real

---

*Proyecto de tesis — Maestría en Inteligencia Artificial · Hotel OLH, Cali, Colombia.*
