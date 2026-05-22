# MetricProcessor

Servicio Flask que **calcula y persiste** los KPIs mensuales (job disparado por el scheduler tras identificar tópicos). Las **consultas** que alimentan la app web viven en [DashboardBackend](../DashboardBackend/) y en el paquete compartido [metricas_read](../../libs/metricas_read/).

## Arranque

```bash
# Copiar variables de entorno
cp .env.example .env

# Instalar dependencias
pip install -r requirements.txt

# Iniciar el servidor (puerto por defecto: 5004)
python app.py
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio |
| `POST` | `/api/v1/metricas/calcular` | Calcula y persiste métricas del período para un archivo procesado |
| `POST` | `/api/v1/metricas/recalcular` | Reaplica scores (suavizado bayesiano) sobre un mes ya materializado en BD |

Variables de entorno **`LAPLACE_PRIOR_M`** (default `0.6`) y **`LAPLACE_PRIOR_C`** (default `5`) controlan el prior; con `LAPLACE_PRIOR_C=0` el score coincide con la proporción bruta de positivos.

### `POST /api/v1/metricas/calcular`

**Body:**
```json
{ "archivo_id": 12 }
```

**Respuesta 200:** incluye `archivo_id`, `estado`, `periodos`, `metricas_por_periodo` (cada ítem con `periodo`, `global` con `score_promedio` suavizado, conteos y `alertas_generadas`), `fecha_metricas`.

### `POST /api/v1/metricas/recalcular`

**Body:**
```json
{ "hotel_id": 1, "anio": 2025, "mes": 11 }
```

**Respuesta 200:** `periodo`, `hotel_id`, `global`, `alertas_generadas`, `fecha_metricas`. **`404`** si no hay fila en `metricas_globales_mensual` para ese mes (`PERIODO_NO_ENCONTRADO`).

Ejemplo de fragmento de respuesta de `/calcular` (un período):

```json
{
  "ok": true,
  "data": {
    "archivo_id": 12,
    "estado": "completed",
    "periodos": [{ "anio": 2025, "mes": 11 }],
    "metricas_por_periodo": [
      {
        "periodo": { "anio": 2025, "mes": 11 },
        "global": {
          "score_promedio": 68.41,
          "cambio_pct_vs_anterior": 2.1,
          "total_reviews": 1432,
          "reviews_positivas": 980,
          "reviews_negativas": 312,
          "reviews_neutras": 140
        },
        "alertas_generadas": [
          { "topico_slug": "ruido", "score_actual": 52.30 }
        ]
      }
    ],
    "fecha_metricas": "2025-11-15T10:05:00Z"
  },
  "error": null
}
```
