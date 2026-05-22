# API Contracts – Sistema de Análisis de Sentimiento de Reviews

> Contratos de API para la comunicación entre los componentes del pipeline de NLP y el Dashboard.
> Base de datos: PostgreSQL · Arquitectura: servicios REST independientes.

---

## Flujo general del pipeline

```
Scheduler
  └─► POST /verificacion/ejecutar
            └─► POST /sentimiento/procesar
                      └─► POST /absa/procesar
                                │     (o POST /absa/procesar-batch → POST /absa/batch/sincronizar si OpenAI Batch)
                                │     — alternativa: POST /topicos/identificar (misma etapa topics_identified)
                                ├─► POST /metricas/calcular   (servicio MetricProcessor — job)
                                │         └─► EMAIL + métricas persistidas en BD
                                └─► POST /metricas/recalcular (MetricProcessor — opcional: re-score de un mes ya persistido)

Dashboard Backend (lecturas para la app web)
  ├─► GET /metricas/kpis
  ├─► GET /metricas/sentimiento-mensual
  ├─► GET /metricas/topicos
  ├─► GET /metricas/topicos/top5
  ├─► GET /metricas/topicos/{slug}/detalle
  ├─► GET /metricas/alertas
  ├─► GET /metricas/reviews
  ├─► GET /metricas/archivos/entrada
  ├─► POST /metricas/archivos/upload
  └─► POST /metricas/recalcular-semestre → POST /metricas/recalcular (MetricProcessor, últimos 6 meses)
```

---

## Convenciones generales

**Base URL por servicio**

| Servicio | Base URL |
|---|---|
| Data Verification & Cleaner | `/api/v1/verificacion` |
| Sentiment Prediction | `/api/v1/sentimiento` |
| ABSAService (ABSA → `review_topicos`, estado `topics_identified`) | `/api/v1/absa` — p. ej. puerto **5005** en local (`PORT` en `.env`; el valor por defecto en código puede coincidir con Sentiment) |
| Topic Identification | `/api/v1/topicos` — alternativa a ABSAService para la misma etapa; no ejecutar ambas sobre el mismo archivo |
| Metric Calculation (job: solo escritura de métricas) | `/api/v1/metricas` — `POST /metricas/calcular` (pipeline) y `POST /metricas/recalcular` (re-score manual de un mes; p. ej. puerto **5004** en local) |
| Dashboard Backend (lecturas de métricas + reviews + archivos en Azure) | `/api/v1/metricas` — expone los `GET` listados abajo, `POST /metricas/recalcular-semestre` (orquesta `POST /metricas/recalcular` en MetricProcessor para los últimos 6 meses), `GET /metricas/archivos/entrada` (blobs pendientes vs `log_archivos`) y `POST /metricas/archivos/upload` (p. ej. puerto **5002** en local) |

La misma ruta lógica `/api/v1/metricas` está dividida en **dos despliegues**: el procesador ejecuta el cálculo batch; el backend del dashboard sirve las consultas que consume el front.

**Headers requeridos**

```
Content-Type:  application/json
```

Endpoints protegidos (Dashboard):
```
Authorization: Bearer {token}
```

No requieren JWT: `/health` de cada servicio y `POST /api/v1/auth/login`.

Requieren token en `Authorization`:
- `POST /api/v1/auth/refresh` (refresh token)
- `POST /api/v1/auth/logout` (access token)

**Envelope de respuesta estándar**

```json
{
  "ok": true | false,
  "data": { ... } | null,
  "error": null | { "codigo": "...", "mensaje": "..." }
}
```

---

## 1. Data Verification & Cleaner Service

### `POST /api/v1/verificacion/ejecutar`

Disparado por el Scheduler. Descarga el blob de origen en **Azure Blob Storage**, valida estructura, ejecuta el
pipeline de limpieza, opcionalmente sube el CSV limpio y vuelca las reviews en la tabla `reviews`.
El campo `plataforma` del body se guarda en `reviews.plataforma` para todas las filas insertadas
(sustituye cualquier valor por fila que viniera en el CSV, si lo hubiera).
Escribe y actualiza `log_archivos` (incluye `hash`: SHA-256 hex del blob de origen descargado).

**Request**

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `hotel_id` | integer | Sí | Identificador del hotel |
| `drive_id_origen` | string | Sí | Ruta del blob de entrada dentro del contenedor Azure configurado (nombre de campo histórico; no es un ID de Google Drive) |
| `nombre_archivo_origen` | string | Sí | Nombre del archivo `.csv` de origen |
| `plataforma` | string | Sí | Origen de las reseñas (1–60 caracteres; p. ej. `booking`, `tripadvisor`) |

```json
{
  "hotel_id": 1,
  "drive_id_origen": "entrada/reviews_olh_nov2025.csv",
  "nombre_archivo_origen": "reviews_olh_nov2025.csv",
  "plataforma": "booking"
}
```

**Response `202 Accepted`**

```json
{
  "ok": true,
  "data": {
    "archivo_id": 12,
    "nombre_archivo_origen": "reviews_olh_nov2025.csv",
    "estado": "cleaned",
    "total_registros": 1500,
    "registros_validos": 1432,
    "registros_descartados": 68,
    "nombre_archivo_limpio": "clean_reviews_olh_2025-11-15.csv",
    "drive_id_limpio": "limpios/reviews_olh_nov2025_clean.csv",
    "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "error": null
}
```

**Response `409 Conflict`** — archivo ya procesado

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "ARCHIVO_YA_PROCESADO",
    "mensaje": "El archivo reviews_olh_nov2025.csv ya fue procesado. Estado actual: completed"
  }
}
```

**Response `422 Unprocessable Entity`** — validación de estructura fallida

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "ESTRUCTURA_INVALIDA",
    "mensaje": "Columnas requeridas ausentes: ['fecha_review', 'texto']"
  }
}
```

---

### `GET /api/v1/verificacion/archivos/{archivo_id}`

Consulta el estado y metadatos de un archivo en el pipeline.
Usada por los componentes siguientes antes de ejecutar su etapa.

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "archivo_id": 12,
    "hotel_id": 1,
    "nombre_archivo_origen": "reviews_olh_nov2025.csv",
    "nombre_archivo_limpio": "clean_reviews_olh_2025-11-15.csv",
    "drive_id_limpio": "limpios/reviews_olh_nov2025_clean.csv",
    "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "estado": "cleaned",
    "total_registros": 1500,
    "registros_validos": 1432,
    "fecha_limpieza": "2025-11-15T08:32:00Z"
  },
  "error": null
}
```

---

### `GET /api/v1/verificacion/archivos?hotel_id=1&estado=cleaned`

Lista archivos en un estado determinado del pipeline.
Usada por Sentiment Prediction para descubrir qué archivos debe procesar.

**Query params**

| Param | Tipo | Descripción |
|---|---|---|
| `hotel_id` | `int` | Filtro por hotel |
| `estado` | `string` | `received` · `validated` · `cleaned` · `predicted` · `topics_identified` · `completed` · `error` |

**Response `200 OK`**

```json
{
  "ok": true,
  "data": [
    {
      "archivo_id": 12,
      "hotel_id": 1,
      "nombre_archivo_limpio": "clean_reviews_olh_2025-11-15.csv",
      "estado": "cleaned",
      "registros_validos": 1432,
      "fecha_limpieza": "2025-11-15T08:32:00Z"
    }
  ],
  "error": null
}
```

---

## 2. Sentiment Prediction Service

### `POST /api/v1/sentimiento/procesar`

Recibe el `archivo_id` y **encola** el trabajo de predicción (API asíncrona: alto volumen).
El worker, al ejecutarse, cargará las reviews desde la tabla `reviews`, predecirá el sentimiento
con el modelo local del servicio (p. ej. checkpoint p91 bajo `SENTIMENT_MODEL_DIR`) y persistirá los resultados en `predicciones_sentimiento`
(`sentimiento`, `confianza`, `prob_negativo`, `prob_neutro`, `prob_positivo`, `modelo_version`),
actualizando `log_archivos.estado = 'predicted'`.

**Request**

```json
{
  "archivo_id": 12
}
```

**Response `202 Accepted`** — trabajo aceptado y encolado

```json
{
  "ok": true,
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "archivo_id": 12,
    "estado": "encolado",
    "mensaje": "El procesamiento se ejecutará de forma asíncrona."
  },
  "error": null
}
```

**Response `400 Bad Request`** — body inválido

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "BODY_INVALIDO",
    "mensaje": "archivo_id es requerido y debe ser un entero positivo"
  }
}
```

**Response `404 Not Found`** — `archivo_id` inexistente en `log_archivos`

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "ARCHIVO_NO_ENCONTRADO",
    "mensaje": "No existe archivo_id=99 en log_archivos."
  }
}
```

**Response `422 Unprocessable Entity`** — el archivo no está en estado `cleaned`

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "ARCHIVO_NO_LISTO",
    "mensaje": "El archivo debe estar en estado 'cleaned' para predecir sentimiento. Estado actual: validated"
  }
}
```

**Response `409 Conflict`** — archivo ya tiene predicciones

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "ARCHIVO_YA_PREDICHO",
    "mensaje": "El archivo_id 12 ya tiene predicciones. Estado: predicted"
  }
}
```

---

### `POST /api/v1/sentimiento/predecir`

Predicción **síncrona** del sentimiento sobre un texto de review. **No** lee ni escribe en la base de datos; solo ejecuta el modelo cargado localmente (misma versión que el batch por archivo).

**Request**

```json
{
  "texto": "La habitación estaba impecable y el personal muy atento."
}
```

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "sentimiento": "positivo",
    "confianza": 0.923,
    "probabilidades": {
      "negativo": 0.012,
      "neutro": 0.065,
      "positivo": 0.923
    },
    "modelo_version": "p91"
  },
  "error": null
}
```

**Response `400 Bad Request`** — body inválido o texto vacío / demasiado largo

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "BODY_INVALIDO",
    "mensaje": "texto no puede estar vacío"
  }
}
```

**Response `500 Internal Server Error`** — fallo al ejecutar el modelo

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "ERROR_INTERNO",
    "mensaje": "Error al ejecutar el modelo de sentimiento."
  }
}
```

---

### `GET /api/v1/sentimiento/archivo/{archivo_id}/resultados`

Devuelve el **estado del job asíncrono** de sentimiento (`estado_proceso`), el **resumen agregado** (`total`, `resumen`) y metadatos (`fecha_prediccion`, `etapa_error`, `mensaje_error` si hubo fallo). **No** lista reviews individuales (el detalle por review queda en la tabla `predicciones_sentimiento` y en consumidores que lean directamente de BD).

`estado_proceso` se deriva de `log_archivos.estado`:

| `log_archivos.estado` | `estado_proceso` |
|-----------------------|------------------|
| `predicted`, `topics_identified`, `completed` | `completado` |
| `error` | `fallido` |
| `cleaned` | `en_proceso` (job encolado o en curso; no distingue de “aún no llamado” solo con BD) |
| `received`, `validated`, u otros | `no_iniciado` |

Si el worker de sentimiento falla, el servicio actualiza `log_archivos` a `estado = error` con `etapa_error = sentiment_prediction` y `mensaje_error` con el mensaje de la excepción.

Usada por orquestadores del pipeline o Topic Identification para saber si puede continuar la etapa siguiente.

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "archivo_id": 12,
    "estado_proceso": "completado",
    "modelo_version": "sentiment-beto-v2.1",
    "total": 1432,
    "resumen": {
      "positivas": 980,
      "negativas": 312,
      "neutras": 140
    },
    "fecha_prediccion": "2025-11-15T09:10:00Z",
    "etapa_error": null,
    "mensaje_error": null
  },
  "error": null
}
```

---

## 3. ABSAService (Aspect-Based Sentiment sobre tópicos)

Servicio independiente que, tras la predicción de sentimiento (`log_archivos.estado = predicted`), ejecuta **ABSA** sobre las reviews del archivo, persiste en `review_topicos` y deja el archivo en `topics_identified`. Sustituye en el pipeline a `POST /topicos/identificar` cuando se despliega ABSA; **no** debe ejecutarse ambos para el mismo `archivo_id`.

**OpenAI Batch (opcional):** con `ABSA_MODEL_BACKEND=llm` y `LLM_PROVIDER=openai`, puede usarse `POST /absa/procesar-batch` y luego `POST /absa/batch/sincronizar` (o el poller interno si `OPENAI_BATCH_POLL_ENABLED=true`). Ver `guidelines/migracion_absa_openai_batches.sql` y tabla `absa_openai_batches`.

### `POST /api/v1/absa/procesar`

Procesamiento **síncrono** (llamadas al modelo según configuración). Mismo envelope de datos que la etapa de tópicos, más `tokens_entrada` y `tokens_salida` cuando aplica el LLM.

**Request**

```json
{
  "archivo_id": 12
}
```

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "archivo_id": 12,
    "estado": "topics_identified",
    "modelo_version": "llm-ollama-llama3.1",
    "total_reviews_procesadas": 1432,
    "total_asignaciones": 2718,
    "distribucion_topicos": [
      { "slug": "limpieza", "menciones": 520 }
    ],
    "tokens_entrada": 120000,
    "tokens_salida": 48000,
    "fecha_topicos": "2025-11-15T09:45:00Z"
  },
  "error": null
}
```

**Errores frecuentes:** `400` `BODY_INVALIDO`; `404` `ARCHIVO_NO_ENCONTRADO`; `409` `ARCHIVO_YA_TOPICADO`, `ESTADO_INVALIDO`, `OPENAI_BATCH_PENDIENTE`; `502` `LLM_NO_DISPONIBLE`, `LLM_RESPUESTA_INVALIDA`; `503` `MODELO_NO_DISPONIBLE`, `LLM_CREDENCIALES_INVALIDAS`.

---

### `POST /api/v1/absa/procesar-batch`

Encola un trabajo **OpenAI Batch API** (JSONL). Requiere cliente OpenAI Batch configurado.

**Request**

```json
{
  "archivo_id": 12
}
```

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "archivo_id": 12,
    "openai_batch_id": "batch_abc123",
    "total_requests": 1432,
    "estado_openai": "validating"
  },
  "error": null
}
```

Si no hay reviews, puede devolver `openai_batch_id: null`, `total_requests: 0` y un `mensaje` indicando que el archivo pasó a `topics_identified`.

**Errores frecuentes:** `409` `OPENAI_BATCH_PENDIENTE`; `502` `LLM_ERROR`.

---

### `POST /api/v1/absa/batch/sincronizar`

Body **opcional**. Sin cuerpo o `{}` procesa todos los batches pendientes en `absa_openai_batches`. Con `{ "openai_batch_id": "batch_abc123" }` solo ese id (debe estar pendiente).

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "resultados": [
      {
        "openai_batch_id": "batch_abc123",
        "archivo_id": 12,
        "estado_openai": "completed",
        "accion": "aplicado",
        "estado": "topics_identified",
        "total_asignaciones": 2718
      }
    ]
  },
  "error": null
}
```

Otros valores de `accion`: `esperando` (batch aún en curso en OpenAI), `fallido`, `omitido`.

**Errores frecuentes:** `404` `OPENAI_BATCH_NO_ENCONTRADO`; `502` `LLM_ERROR`.

---

### `GET /health` (ABSAService)

Health check sin prefijo `/api/v1` (típico en monitoreo).

**Response `200 OK`**

```json
{
  "ok": true,
  "service": "absa-service",
  "version": "0.1.0",
  "status": "up"
}
```

---

## 4. Topic Identification Service (estado actual del repo)

Etapa **opcional** frente a la **sección 3 (ABSAService)**: ambas llevan el archivo a `topics_identified` y escriben `review_topicos`.

**Estado en `sources/apis`:** actualmente no hay un servicio desplegado bajo `/api/v1/topicos`; en este repositorio la etapa activa para tópicos es **ABSAService** (`/api/v1/absa/*`).

### `POST /api/v1/topicos/identificar`

Recibe el `archivo_id`, lee las reviews con sentimiento **predicted** desde BD, identifica los tópicos
referenciados en cada review con el modelo activo del registry y persiste en `review_topicos`.
Actualiza `log_archivos.estado = 'topics_identified'`.

**Request**

```json
{
  "archivo_id": 12
}
```

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "archivo_id": 12,
    "estado": "topics_identified",
    "modelo_version": "topic-beto-v1.4",
    "total_reviews_procesadas": 1432,
    "total_asignaciones": 2718,
    "distribucion_topicos": [
      { "slug": "limpieza",                "menciones": 520 },
      { "slug": "atencion_cliente",        "menciones": 480 },
      { "slug": "instalaciones_servicios", "menciones": 380 },
      { "slug": "ruido",                   "menciones": 310 },
      { "slug": "wifi",                    "menciones": 290 },
      { "slug": "comodidad",               "menciones": 270 },
      { "slug": "calidad_precio",          "menciones": 250 },
      { "slug": "desayuno_gastronomia",    "menciones": 218 }
    ],
    "fecha_topicos": "2025-11-15T09:45:00Z"
  },
  "error": null
}
```

---

### `GET /api/v1/topicos/review/{review_id}`

Devuelve los tópicos asignados a una review específica con su fragmento de texto y el sentimiento
específico de ese tópico dentro de la review. El sentimiento del tópico puede diferir del sentimiento
global de la review (ej. una review neutra puede tener un tópico positivo y otro negativo).
Usada por el Dashboard para el modal de detalle de un tópico.

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "review_id": 5001,
    "topicos": [
      {
        "topico_id": 1,
        "slug": "limpieza",
        "nombre": "Limpieza",
        "score_topico": 0.912,
        "sentimiento": "positivo",
        "fragmento": "La habitación estaba impecable cada día."
      },
      {
        "topico_id": 6,
        "slug": "desayuno_gastronomia",
        "nombre": "Desayuno / Gastronomía",
        "score_topico": 0.784,
        "sentimiento": "negativo",
        "fragmento": "El desayuno era escaso y frío."
      }
    ]
  },
  "error": null
}
```

---

## 5. Metric Calculation Service

**Despliegue:** el cálculo vive en **MetricProcessor**: `POST /api/v1/metricas/calcular` (job del pipeline) y `POST /api/v1/metricas/recalcular` (reaplica scores sobre conteos ya persistidos para un mes). Las lecturas de métricas bajo el mismo prefijo `/api/v1/metricas` las expone **DashboardBackend**; la lógica SQL de lectura está centralizada en el paquete compartido `sources/libs/metricas_read`.

### `POST /api/v1/metricas/calcular` (MetricProcessor)

Calcula y persiste todas las métricas del período cubierto por el archivo en
`metricas_globales_mensual` y `metricas_topico_mensual`. Genera registros en `alertas`
para los tópicos cuyo score esté por debajo del umbral configurado.
Actualiza `log_archivos.estado = 'completed'`.

**Fórmulas del `score_promedio` (suavizado bayesiano / prior del corpus):**

Sea `positivas` = `reviews_positivas` (global) o `menciones_positivas` (tópico), y `total` = `total_reviews` o `total_menciones`.

\[
\text{score\_promedio} = \frac{\text{positivas} + C \cdot m}{\text{total} + C} \times 100
\]

- `m` ∈ [0, 1] y `C` ≥ 0 se configuran en MetricProcessor con variables de entorno **`LAPLACE_PRIOR_M`** (default `0.6`) y **`LAPLACE_PRIOR_C`** (default `5`). Con **`C = 0`** se recupera la proporción bruta \((\text{positivas}/\text{total})\times 100\).
- Si el denominador efectivo deja `total = 0` (sin reviews/menciones en el mes), el score se persiste como **`0.00`** (NOT NULL en BD).

**Archivos multi-mes:** un archivo puede contener reviews de varios meses naturales.
El job NO bloquea: calcula un UPSERT por cada `(anio, mes)` distinto hallado en
`reviews.fecha_review`. La respuesta enumera todos los períodos tocados.

**Idempotencia:**
- `metricas_globales_mensual` / `metricas_topico_mensual`: `INSERT … ON CONFLICT DO UPDATE`
  (claves únicas `(hotel_id, anio, mes)` y `(hotel_id, topico_id, anio, mes)`).
- `alertas` (sin `UNIQUE` de negocio en DDL): `DELETE WHERE (hotel_id, anio, mes) AND resuelta = FALSE`
  antes de re-insertar; alertas con `resuelta = TRUE` no se eliminan.

**Request (`/calcular`)**

```json
{
  "archivo_id": 12
}
```

**Response `200 OK` (`/calcular`)**

```json
{
  "ok": true,
  "data": {
    "archivo_id": 12,
    "estado": "completed",
    "periodos": [
      { "anio": 2025, "mes": 10 },
      { "anio": 2025, "mes": 11 }
    ],
    "metricas_por_periodo": [
      {
        "periodo": { "anio": 2025, "mes": 10 },
        "global": {
          "score_promedio": 65.80,
          "cambio_pct_vs_anterior": null,
          "total_reviews": 620,
          "reviews_positivas": 408,
          "reviews_negativas": 148,
          "reviews_neutras": 64
        },
        "alertas_generadas": [
          { "topico_slug": "ruido", "score_actual": 54.10 }
        ]
      },
      {
        "periodo": { "anio": 2025, "mes": 11 },
        "global": {
          "score_promedio": 68.40,
          "cambio_pct_vs_anterior": 2.60,
          "total_reviews": 812,
          "reviews_positivas": 555,
          "reviews_negativas": 177,
          "reviews_neutras": 80
        },
        "alertas_generadas": [
          { "topico_slug": "ruido",  "score_actual": 52.30 },
          { "topico_slug": "wifi",   "score_actual": 58.10 }
        ]
      }
    ],
    "fecha_metricas": "2025-11-15T10:05:00Z"
  },
  "error": null
}
```

### `POST /api/v1/metricas/recalcular` (MetricProcessor)

Vuelve a calcular `score_promedio`, `cambio_pct_vs_anterior` y alertas **leyendo los conteos ya guardados** en las tablas mensuales (no re-cuenta desde `reviews`). Responde **`404`** con código `PERIODO_NO_ENCONTRADO` si no existe fila global para ese mes.

> Tras cambiar `LAPLACE_PRIOR_M` / `LAPLACE_PRIOR_C` o para alinear históricos, conviene invocar `/recalcular` en **orden cronológico** por mes: el `cambio_pct_vs_anterior` del mes siguiente se basa en el `score_promedio` ya persistido del mes anterior.

**Request (`/recalcular`)**

```json
{
  "hotel_id": 1,
  "anio": 2025,
  "mes": 11
}
```

**Response `200 OK` (`/recalcular`)**

```json
{
  "ok": true,
  "data": {
    "periodo": { "anio": 2025, "mes": 11 },
    "hotel_id": 1,
    "global": {
      "score_promedio": 68.41,
      "cambio_pct_vs_anterior": 2.60,
      "total_reviews": 812,
      "reviews_positivas": 555,
      "reviews_negativas": 177,
      "reviews_neutras": 80
    },
    "alertas_generadas": [],
    "fecha_metricas": "2025-11-15T10:05:00Z"
  },
  "error": null
}
```

---

## 7. Autenticación (DashboardBackend)

### `POST /api/v1/auth/login`

Autentica usuario activo y retorna `access_token` + `refresh_token`.

**Request**

```json
{
  "username": "admin",
  "password": "secret"
}
```

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "access_token": "<jwt>",
    "refresh_token": "<jwt>",
    "token_type": "Bearer"
  },
  "error": null
}
```

### `POST /api/v1/auth/refresh`

Requiere `Authorization: Bearer {refresh_token}`. Retorna nuevo `access_token`.

### `POST /api/v1/auth/logout`

Requiere `Authorization: Bearer {access_token}` y body con `refresh_token`. Revoca ambos tokens.

---

## 8. Health checks operativos

Los siguientes endpoints existen en `sources/apis/*/app.py` y no requieren autenticación:

- `GET /health` (DataVerificationCleanner)
- `GET /health` (SentimentPrediction)
- `GET /health` (ABSAService)
- `GET /health` (MetricProcessor)
- `GET /health` (DashboardBackend)


### `GET /api/v1/metricas/kpis?hotel_id=1&anio=2025&mes=11` (DashboardBackend)

KPIs mensuales agregados para cabecera de dashboard. Consulta directamente
`metricas_globales_mensual` que el job ya dejó pre-calculado.

**Nota:** payload canónico de `GET /api/v1/metricas/kpis`.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `hotel_id` | `int` | Sí | Hotel a consultar |
| `anio` | `int` | Sí | Año del período (mínimo `2020`) |
| `mes` | `int` | Sí | Mes del período (1–12) |

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "sentimiento_promedio": {
      "score": 68.40,
      "cambio_pct": 2.1,
      "tendencia": "up"
    },
    "reviews_analizadas": 1432,
    "topicos_con_alerta": 2
  },
  "error": null
}
```

Si no existen métricas para el período, se responde `200` con `data` en ceros:

```json
{
  "ok": true,
  "data": {
    "sentimiento_promedio": {
      "score": 0.0,
      "cambio_pct": 0.0,
      "tendencia": "stable"
    },
    "reviews_analizadas": 0,
    "topicos_con_alerta": 0
  },
  "error": null
}
```

**Códigos de error**

| `error.codigo` | HTTP | Descripción |
|---|---|---|
| `PARAMETROS_INVALIDOS` | `400` | Parámetros requeridos ausentes o inválidos (`hotel_id`, `anio`, `mes`) |
| `ERROR_INTERNO` | `500` | Fallo inesperado al consultar la BD |

---

### `GET /api/v1/metricas/sentimiento-mensual?hotel_id=1&meses=12` (DashboardBackend)

Serie temporal de score de sentimiento para el gráfico de línea. Consulta directamente
`metricas_globales_mensual` que el job ya dejó pre-calculado.

**Nota:** payload canónico de `GET /api/v1/metricas/sentimiento-mensual`.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `hotel_id` | `int` | Sí | Hotel a consultar |
| `meses` | `int` | No | Últimos N meses incluyendo el actual (default: `12`, rango: 1–24). Se ignora si se usan `desde` y `hasta`. |
| `desde` | `string` | No | Inicio del rango en formato `YYYY-MM` (requiere `hasta`) |
| `hasta` | `string` | No | Fin del rango en formato `YYYY-MM` (requiere `desde`) |

**Response `200 OK`**

```json
{
  "ok": true,
  "data": [
    { "anio": 2025, "mes": 10, "score_promedio": 65.80, "total_reviews": 620 },
    { "anio": 2025, "mes": 11, "score_promedio": 68.40, "total_reviews": 812 }
  ],
  "error": null
}
```

**Códigos de error**

| `error.codigo` | HTTP | Descripción |
|---|---|---|
| `PARAMETROS_INVALIDOS` | `400` | `hotel_id` ausente o inválido; `meses` fuera de rango; `desde`/`hasta` con formato incorrecto, incompleto o `desde > hasta` |
| `ERROR_INTERNO` | `500` | Fallo inesperado al consultar la BD |

---

### `GET /api/v1/metricas/topicos?hotel_id=1&anio=2025&mes=11` (DashboardBackend)

Métricas por tópico del mes para el grid / tabla de rendimiento. Lee
`metricas_topico_mensual` y el catálogo `topicos`.

**Nota:** payload canónico de `GET /api/v1/metricas/topicos`.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `hotel_id` | `int` | Sí | Hotel a consultar |
| `anio` | `int` | Sí | Año del período |
| `mes` | `int` | Sí | Mes del período (1–12) |
| `tipo` | `string` | No | `clave` · `adicional` · (vacío = todos) |
| `solo_alertas` | `bool` | No | `true` para retornar solo tópicos con alerta activa |

**Response `200 OK`**

Misma forma que la tabla de `GET /api/v1/metricas/topicos` (lista de objetos con
`topico_id`, `slug`, `nombre`, `tipo`, `score_promedio`, `cambio_pct_vs_anterior`,
`total_menciones`, `alerta`, `tendencia`).

**Códigos de error**

| `error.codigo` | HTTP | Descripción |
|---|---|---|
| `PARAMETROS_INVALIDOS` | `400` | Parámetros requeridos ausentes o inválidos |
| `ERROR_INTERNO` | `500` | Fallo inesperado al consultar la BD |

---

### `GET /api/v1/metricas/topicos/top5?hotel_id=1&anio=2025&mes=11` (DashboardBackend)

Top 5 tópicos más críticos del período (menor score primero). Usa la misma fuente
de datos que `GET /api/v1/metricas/topicos` (`metricas_topico_mensual` + `topicos`),
pero con orden ascendente y `LIMIT 5`.

**Nota:** payload canónico de `GET /api/v1/metricas/topicos/top5`.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `hotel_id` | `int` | Sí | Hotel a consultar |
| `anio` | `int` | Sí | Año del período (mínimo `2020`) |
| `mes` | `int` | Sí | Mes del período (1–12) |

**Response `200 OK`**

```json
{
  "ok": true,
  "data": [
    { "posicion": 1, "slug": "ruido", "nombre": "Ruido", "score_promedio": 52.30, "alerta": true },
    { "posicion": 2, "slug": "calidad_precio", "nombre": "Relación calidad-precio", "score_promedio": 58.10, "alerta": true },
    { "posicion": 3, "slug": "wifi", "nombre": "WiFi", "score_promedio": 61.00, "alerta": false },
    { "posicion": 4, "slug": "instalaciones_servicios", "nombre": "Instalaciones y servicios", "score_promedio": 63.20, "alerta": false },
    { "posicion": 5, "slug": "desayuno_gastronomia", "nombre": "Desayuno / Gastronomía", "score_promedio": 66.50, "alerta": false }
  ],
  "error": null
}
```

**Códigos de error**

| `error.codigo` | HTTP | Descripción |
|---|---|---|
| `PARAMETROS_INVALIDOS` | `400` | Parámetros requeridos ausentes o inválidos (`hotel_id`, `anio`, `mes`) |
| `ERROR_INTERNO` | `500` | Fallo inesperado al consultar la BD |

---

### `GET /api/v1/metricas/alertas?hotel_id=1&resuelta=false` (DashboardBackend)

Lista de alertas para el panel de alertas del dashboard.

**Nota:** payload canónico de `GET /api/v1/metricas/alertas`.

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `hotel_id` | `int` | Sí | Hotel a consultar |
| `resuelta` | `bool` | No | `false` = solo activas (default) · `true` = solo resueltas |

**Response `200 OK`**

```json
{
  "ok": true,
  "data": [
    {
      "alerta_id": 5,
      "topico_slug": "ruido",
      "topico_nombre": "Ruido",
      "anio": 2025,
      "mes": 11,
      "score_actual": 52.30,
      "umbral_usado": 65,
      "mensaje": "Score de Ruido cayó a 52.3%, por debajo del umbral de 65%.",
      "generada_en": "2025-11-15T10:05:00Z"
    }
  ],
  "error": null
}
```

**Códigos de error**

| `error.codigo` | HTTP | Descripción |
|---|---|---|
| `PARAMETROS_INVALIDOS` | `400` | Parámetros requeridos ausentes o inválidos (`hotel_id`, `resuelta`) |
| `ERROR_INTERNO` | `500` | Fallo inesperado al consultar la BD |

---

## 9. Métricas de lectura complementarias

### `GET /api/v1/metricas/topicos/{slug}/detalle?hotel_id=1&anio=2025&mes=11` (DashboardBackend)

Detalle completo de un tópico para el modal de detalle.
Incluye score, cambio, estado de alerta, desglose de menciones y fragmentos reales de reviews.

**Path params**

| Param | Tipo | Descripción |
|---|---|---|
| `slug` | `string` | Identificador del tópico (ej: `ruido`, `limpieza`) |

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `hotel_id` | `int` | Sí | Hotel a consultar |
| `anio` | `int` | Sí | Año del período |
| `mes` | `int` | Sí | Mes del período (1–12) |

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "slug": "ruido",
    "nombre": "Ruido",
    "score_promedio": 52.30,
    "cambio_pct_vs_anterior": -5.2,
    "alerta": true,
    "umbral_alerta": 65,
    "menciones": {
      "total": 310,
      "positivas": 82,
      "negativas": 193,
      "neutras": 35
    },
    "fragmentos_destacados": [
      { "sentimiento": "negativo", "fragmento": "El ruido de la calle no nos dejó descansar.",      "confianza": 0.951 },
      { "sentimiento": "negativo", "fragmento": "Se escucha todo desde el pasillo.",                 "confianza": 0.912 },
      { "sentimiento": "positivo", "fragmento": "Las habitaciones interiores son muy tranquilas.",   "confianza": 0.883 }
    ]
  },
  "error": null
}
```

---

### `GET /api/v1/metricas/reviews?hotel_id=1&fecha_desde=2025-10-01&fecha_hasta=2025-11-15` (DashboardBackend)

Listado paginado de reviews del hotel con predicción de sentimiento y tópicos asociados (**Reviews Explorer**).
Origen: tablas `reviews`, `predicciones_sentimiento`, `review_topicos` y `topicos`.
Complementa `GET /api/v1/topicos/review/{review_id}` (detalle de tópicos de una sola review).

**Query params**

| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `hotel_id` | `int` | Sí | Hotel a consultar |
| `fecha_desde` | `date` (ISO) | No | Inclusivo. Filtra `reviews.fecha_review` ≥ esta fecha. Si se omite junto con `fecha_hasta`, el backend puede aplicar un rango por defecto (p. ej. últimos 30 días). |
| `fecha_hasta` | `date` (ISO) | No | Inclusivo. Filtra `reviews.fecha_review` ≤ esta fecha. |
| `sentimiento` | `string` | No | `positivo` · `negativo` · `neutro` — filtra por sentimiento global en `predicciones_sentimiento`. |
| `topico_slug` | `string` | No | Solo reviews con asignación para el tópico con este `slug`. Si se envía junto con `topico_id`, prevalece `topico_slug`. |
| `topico_id` | `int` | No | Alternativa a `topico_slug`. |
| `page` | `int` | No | Número de página (base 1, default: `1`). |
| `page_size` | `int` | No | Tamaño de página (default: `20`, máx. `100`). |
| `orden` | `string` | No | `fecha_desc` (default) · `fecha_asc` — orden por `reviews.fecha_review`. |

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "review_id": 5001,
        "hotel_id": 1,
        "fecha_review": "2023-10-12",
        "texto_limpio": "Our stay was absolutely magnificent from the moment we arrived.",
        "plataforma": "Booking.com",
        "idioma": "en",
        "titulo": "Excellent Stay in the Master Suite",
        "prediccion": {
          "sentimiento": "positivo",
          "confianza": 0.923,
          "modelo_version": "sentiment-beto-v2.1"
        },
        "topicos": [
          {
            "topico_id": 1,
            "slug": "limpieza",
            "nombre": "Limpieza",
            "score_topico": 0.912,
            "sentimiento": "positivo",
            "fragmento": "La habitación estaba impecable cada día."
          }
        ]
      }
    ],
    "paginacion": {
      "page": 1,
      "page_size": 20,
      "total": 1432,
      "total_pages": 72
    }
  },
  "error": null
}
```

**Response `422 Unprocessable Entity`** — parámetros de filtro inválidos

```json
{
  "ok": false,
  "data": null,
  "error": {
    "codigo": "PARAMETROS_INVALIDOS",
    "mensaje": "fecha_desde no puede ser posterior a fecha_hasta"
  }
}
```

---

### `GET /api/v1/metricas/archivos/entrada` (DashboardBackend)

Lista los blobs en Azure Blob Storage **solo en el nivel del prefijo** (sin archivos en subcarpetas): si `AZURE_BLOB_PREFIX_UPLOAD` está vacío o es solo `/`, solo blobs en la raíz del contenedor (nombre sin `/`, p. ej. `informe.csv`); si tiene valor (p. ej. `entrada`), solo `entrada/archivo.csv` y no `entrada/sub/archivo.csv`. También devuelve **todas** las filas de `log_archivos` (archivos en pipeline o ya procesados), **sin filtrar** por `drive_id_origen` ni por prefijo. Cada ítem de `en_pipeline` incluye, entre otros campos, `total_registros`, `registros_validos` y `registros_descartados` (estadísticas del proceso de limpieza). Un blob se considera **pendiente de lectura** (aún no procesado respecto a lo registrado en BD) si no hay una fila con el mismo `drive_id_origen` y, en respaldo, si el nombre base no coincide con un `nombre_archivo_origen` ya registrado (índice único por nombre).

**Query (opcional)**

| Parámetro | Descripción |
|---|---|
| `limite` | Entero entre 1 y 5000: tope máximo de blobs a recorrer en Azure. Si se alcanza el tope y pudieran existir más resultados, `data.truncado` es `true`. |

**Variables de entorno:** `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER` (obligatorios para Azure). `AZURE_BLOB_PREFIX_UPLOAD` es opcional: vacío = raíz del contenedor en el listado de blobs. `AZURE_BLOB_LIST_EXCLUDE_PREFIXES` (opcional, valores separados por coma): prefijos de ruta que no deben aparecer en el listado de blobs; por defecto el backend excluye `limpios` (salida de CSV limpios del pipeline). Asigna vacío en `.env` si quieres listar también bajo `limpios/`.

**Consumidores:** aplicación web del dashboard u operación del pipeline.

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "prefijo": "entrada",
    "pendientes": [
      {
        "blob_path": "entrada/nuevo.csv",
        "tamano_bytes": 1024,
        "ultima_modificacion": "2025-11-15T10:00:00+00:00"
      }
    ],
    "en_pipeline": [
      {
        "id": 12,
        "hotel_id": 1,
        "nombre_archivo_origen": "reviews_ejemplo.csv",
        "drive_id_origen": "entrada/reviews_ejemplo.csv",
        "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "total_registros": 500,
        "registros_validos": 480,
        "registros_descartados": 20,
        "estado": "cleaned",
        "etapa_error": null,
        "mensaje_error": null,
        "fecha_recepcion": "2025-11-15T09:00:00+00:00",
        "fecha_limpieza": "2025-11-15T09:05:00+00:00",
        "fecha_prediccion": null,
        "fecha_topicos": null,
        "fecha_metricas": null
      }
    ],
    "truncado": false
  },
  "error": null
}
```

Si no se envía `limite`, el campo `truncado` no se incluye en `data`.

**Códigos de error**

| `error.codigo` | HTTP | Descripción |
|---|---|---|
| `PARAMETROS_INVALIDOS` | `400` | `limite` inválido o fuera de rango |
| `ERROR_LISTADO_AZURE` | `502` | Error al listar blobs en Azure Storage |
| `CREDENCIALES_AZURE_INVALIDAS` | `503` | Cadena de conexión o contenedor Azure inválido o ausente |
| `ERROR_INTERNO` | `500` | Error inesperado (p. ej. base de datos) |

---

### `POST /api/v1/metricas/archivos/upload` (DashboardBackend)

Sube un archivo al contenedor de Azure Blob Storage usando el prefijo configurado (`AZURE_BLOB_PREFIX_UPLOAD`). El cuerpo es **`multipart/form-data`** con el campo **`archivo`** (archivo binario).

El backend calcula el **SHA-256** (hex) del contenido y consulta `log_archivos.hash`. Si ya existe ese hash, responde **`409`** y **no** sube el blob. Si el hash es nuevo, sube el archivo y responde **`200`**. **No inserta** fila en `log_archivos` (la deduplicación solo aplica frente a hashes ya registrados por otras rutas o procesos).

**Variables de entorno:** `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER`, `AZURE_BLOB_PREFIX_UPLOAD`; límite de tamaño opcional `UPLOAD_MAX_BYTES` (default 50 MiB).

**Response `200 OK`**

```json
{
  "ok": true,
  "data": {
    "blob_path": "entrada/reviews_ejemplo.csv",
    "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "nombre_archivo": "reviews_ejemplo.csv"
  },
  "error": null
}
```

**Códigos de error**

| `error.codigo` | HTTP | Descripción |
|---|---|---|
| `PARAMETROS_INVALIDOS` | `400` | Falta el campo `archivo` o el nombre es inválido |
| `ARCHIVO_YA_SUBIDO` | `409` | El hash SHA-256 ya está en `log_archivos` |
| `ARCHIVO_DEMASIADO_GRANDE` | `413` | Supera el tamaño máximo configurado |
| `ERROR_SUBIDA_AZURE` | `502` | Error HTTP u operación fallida al subir al blob |
| `CREDENCIALES_AZURE_INVALIDAS` | `503` | Cadena de conexión o contenedor Azure inválido o ausente |
| `ERROR_INTERNO` | `500` | Error inesperado en el servidor |

---

### `POST /api/v1/metricas/recalcular-semestre` (DashboardBackend)

Orquesta el **re-score** de los **últimos 6 meses naturales** incluyendo el mes actual (rolling), llamando en **orden cronológico ascendente** a MetricProcessor `POST /api/v1/metricas/recalcular` por cada `(anio, mes)` (mismo contrato que §5). Útil tras cambiar `LAPLACE_PRIOR_M` / `LAPLACE_PRIOR_C` o para alinear un bloque reciente sin invocar mes a mes desde el cliente.

**Autenticación:** JWT (`Authorization: Bearer`).

**Variables de entorno (DashboardBackend):** `METRIC_PROCESSOR_URL` (base del servicio MetricProcessor, sin barra final; default `http://localhost:5004`), `METRIC_PROCESSOR_TIMEOUT_SECONDS` (timeout **por cada** POST a `/recalcular`; el peor caso total es hasta 6× ese valor).

**Request**

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `hotel_id` | integer | Sí | Hotel cuyas métricas mensuales se recalculan |

```json
{
  "hotel_id": 1
}
```

**Response `200 OK`**

Resumen síncrono (los meses sin fila global en BD aparecen en `fallidos` con el código devuelto por MetricProcessor, p. ej. `PERIODO_NO_ENCONTRADO`).

```json
{
  "ok": true,
  "data": {
    "hotel_id": 1,
    "primer_periodo": { "anio": 2025, "mes": 12 },
    "ultimo_periodo": { "anio": 2026, "mes": 5 },
    "periodos_solicitados": 6,
    "exitos": 5,
    "fallos": 1,
    "fallidos": [
      {
        "anio": 2025,
        "mes": 12,
        "http_status": 404,
        "codigo": "PERIODO_NO_ENCONTRADO",
        "mensaje": "No hay métricas globales para hotel_id=1 2025-12"
      }
    ],
    "fecha_inicio": "2026-05-12T18:00:00+00:00",
    "fecha_fin": "2026-05-12T18:00:04+00:00"
  },
  "error": null
}
```

**Códigos de error**

| `error.codigo` | HTTP | Descripción |
|---|---|---|
| `BODY_INVALIDO` | `400` | Body vacío o `hotel_id` inválido |
| `METRIC_PROCESSOR_INDISPONIBLE` | `503` | No se pudo conectar con MetricProcessor o timeout en una llamada |
| `ERROR_INTERNO` | `500` | Error inesperado en DashboardBackend |

---

## Códigos de error comunes

| Código | HTTP | Descripción |
|---|---|---|
| `BODY_INVALIDO` | `400` | Body JSON inválido o campos requeridos ausentes (varios `POST`; en `POST /metricas/recalcular-semestre`: `hotel_id`) |
| `METRIC_PROCESSOR_INDISPONIBLE` | `503` | DashboardBackend no alcanza MetricProcessor (`POST /metricas/recalcular-semestre`) |
| `ARCHIVO_YA_SUBIDO` | `409` | El hash del archivo ya existe en `log_archivos` (`POST /metricas/archivos/upload`) |
| `ARCHIVO_YA_PROCESADO` | `409` | El archivo ya fue procesado en una ejecución anterior |
| `ARCHIVO_YA_PREDICHO` | `409` | El archivo ya tiene predicciones de sentimiento |
| `ARCHIVO_YA_TOPICADO` | `409` | El archivo ya tiene tópicos identificados |
| `ESTRUCTURA_INVALIDA` | `422` | El CSV no tiene las columnas requeridas |
| `PARAMETROS_INVALIDOS` | `400` / `422` | Query inválido (`GET /metricas/archivos/entrada`: `limite` fuera de rango); filtros o paginación inválidos en otros endpoints (p. ej. `422` en `GET /metricas/reviews`) |
| `ERROR_LISTADO_AZURE` | `502` | Error al listar blobs en Azure (`GET /metricas/archivos/entrada`) |
| `ARCHIVO_NO_LISTO` | `422` | El archivo no está en estado `cleaned` (p. ej. `POST /sentimiento/procesar`) |
| `ARCHIVO_NO_ENCONTRADO` | `404` | No se encontró el archivo en almacenamiento o en BD |
| `ESTADO_INVALIDO` | `409` | El archivo no está en el estado requerido para esta operación |
| `HOTEL_NO_ASIGNADO` | `422` | El archivo existe pero `hotel_id` es NULL; no puede asignarse el cálculo a ningún hotel |
| `SIN_REVIEWS` | `422` | El archivo no tiene reviews asociadas; no hay datos que agregar |
| `MODELO_NO_DISPONIBLE` | `503` | No se pudo recuperar el modelo desde el registry |
| `OPENAI_BATCH_PENDIENTE` | `409` | Hay un batch OpenAI sin sincronizar para este archivo (ABSAService) |
| `OPENAI_BATCH_NO_ENCONTRADO` | `404` | El `openai_batch_id` no existe en `absa_openai_batches` (sincronizar) |
| `LLM_NO_DISPONIBLE` | `502` | Error de red o tiempo de espera con el proveedor LLM |
| `LLM_RESPUESTA_INVALIDA` | `502` | El LLM devolvió contenido no parseable tras reintentos (ABSA síncrono) |
| `LLM_CREDENCIALES_INVALIDAS` | `503` | API key u autenticación del proveedor rechazada |
| `LLM_ERROR` | `502` | Error genérico del proveedor (p. ej. OpenAI Batch) |
| `ERROR_INTERNO` | `500` | Error inesperado en el procesamiento |

---

## Estados del pipeline (`log_archivos.estado`)

```
received → validated → cleaned → predicted → topics_identified → completed
                                                           ↓
                                                    (en cualquier etapa)
                                                         error
```

| Estado | Responsable | Significado |
|---|---|---|
| `received` | Data Verification | Archivo registrado / encontrado en almacenamiento (Azure Blob) |
| `validated` | Data Verification | Estructura y columnas correctas |
| `cleaned` | Data Verification | Pipeline de limpieza ejecutado, reviews en BD |
| `predicted` | Sentiment Prediction | Sentimiento calculado para todas las reviews |
| `topics_identified` | ABSAService o Topic Identification | Tópicos identificados y almacenados en `review_topicos` |
| `completed` | Metric Calculation | Métricas calculadas, disponible para el Dashboard |
| `error` | Cualquiera | Fallo en alguna etapa (`etapa_error` indica cuál) |
