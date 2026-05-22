# Plan de implementación — generación de métricas y dashboard

**Uso:** documento de referencia e *input* para trabajo iterativo (MetricProcessor → BD → DashboardBackend → front).

**Principio:** el job de métricas **escribe** tablas pre-calculadas; el dashboard **solo lee** y grafica (salvo el explorer de reviews).

---

## Referencias rápidas

| Recurso | Ruta / notas |
|--------|----------------|
| DDL métricas y alertas | `guidelines/ddl_bd.sql` — `metricas_globales_mensual`, `metricas_topico_mensual`, `alertas` |
| Contrato API | `guidelines/api-contracts.md`, OpenAPI si aplica |
| Job de cálculo | `sources/apis/MetricProcessor/routes/metricas.py` — `POST /api/v1/metricas/calcular`, `POST /api/v1/metricas/recalcular` |
| Servicio de cálculo (escritura) | `sources/apis/MetricProcessor/services/metricas_service.py` |
| Lecturas de métricas (compartido) | `sources/libs/metricas_read/` — repositorio + `obtener_*` usados por el dashboard |
| Rutas GET dashboard | `sources/apis/DashboardBackend/routes/dashboard.py` — `/api/v1/metricas/*` (excepto mocks legacy en `dummy_responses.py` si aplica) |
| UI Executive (secciones) | `sources/app/olh-sentiment-ia/app/dashboard/page.tsx` |

---

## Fase 0 — Cimientos (antes de secciones de producto)

- [x] Definir resolución **`archivo_id` → `hotel_id`, períodos** (archivos multi-mes soportados; partición por `fecha_review`).
- [x] Documentar reglas de agregación alineadas al DDL:
  - [x] Score global: `((reviews_positivas + C·m) / (total_reviews + C)) * 100` en `metricas_globales_mensual` (`LAPLACE_PRIOR_M`, `LAPLACE_PRIOR_C`; `C=0` → proporción bruta).
  - [x] Score por tópico: `((menciones_positivas + C·m) / (total_menciones + C)) * 100` en `metricas_topico_mensual`.
- [x] Definir **idempotencia** del job (UPSERT en métricas; delete+insert en alertas no-resueltas).
- [x] Definir fuente de **umbral de alerta** por tópico (`topicos.umbral_alerta`) y cuándo insertar `alertas`.
- [x] Tests mínimos de verificación con datos de ejemplo (reglas puras en `tests/test_metricas_reglas.py`; rutas en `tests/test_calcular_route.py`).

---

## Sección 1 — Hero KPIs / cabecera (`GET /metricas/kpis`)

**Tabla principal:** `metricas_globales_mensual`  
**Opcional:** mejor/peor tópico desde `metricas_topico_mensual` (mismo mes).

- [x] Calcular y persistir: `total_reviews`, conteos ±, `score_promedio`, `cambio_pct_vs_anterior`, `total_alertas`.
- [x] Implementar lectura en DashboardBackend sustituyendo `dummy.kpis()`.
- [x] Validar respuesta contra contrato (OpenAPI / `guidelines/api-contracts.md`).

---

## Sección 2 — Tendencia / serie temporal (`GET /metricas/sentimiento-mensual`)

**Tabla:** histórico de `metricas_globales_mensual` (varios meses).

- [x] Asegurar que cada ejecución del job deja el mes actual **consistente** (y meses previos ya calculados).
- [x] Implementar endpoint con filtro por `hotel_id` y rango (`meses` o `desde`/`hasta`) en DashboardBackend.
- [x] Sustituir `dummy.sentimiento_mensual()`.

---

## Sección 3 — Grid de tópicos / categorías (`GET /metricas/topicos`)

**Tabla:** `metricas_topico_mensual`.

- [x] Por cada tópico con actividad en el mes: conteos, `score_promedio`, `cambio_pct_vs_anterior`, `alerta`.
- [x] Implementar lectura con query params (`hotel_id`, `anio`, `mes`, filtros opcionales) en DashboardBackend (`GET /api/v1/metricas/topicos`).
- [x] Sustituir `dummy.topicos()` por datos reales (paquete `metricas_read`).

---

## Sección 4 — Top 5 críticos (`GET /metricas/topicos/top5`)

**Origen:** misma data que sección 3 (solo consulta).

- [x] Query: orden por score ascendente (o regla acordada), `LIMIT 5`.
- [x] Sustituir `dummy.top5()` por datos reales.

---

## Sección 5 — Detalle de tópico (`GET /metricas/topicos/<slug>/detalle`)

**Agregados:** `metricas_topico_mensual` + metadatos de `topicos`.  
**Fragmentos:** lectura desde reviews / predicciones (no suele pre-calcularse en tablas mensuales).

- [x] Montar JSON de números (score, delta, umbral, menciones ±) desde métricas + catálogo de tópicos.
- [x] Sub-fase opcional: fragmentos destacados desde tablas de reviews.
- [x] Sustituir `dummy.topico_detalle(slug)` por datos reales.

---

## Sección 6 — Alertas (`GET /metricas/alertas`)

**Tabla:** `alertas` (+ posible join con `topicos`).

- [x] En el job: al persistir métricas por tópico, crear/actualizar alertas según umbral (evitar duplicados por período/tópico si aplica).
- [x] Implementar listado con filtro `resuelta` / `hotel_id`.
- [x] Sustituir `dummy.alertas()`.

---

## Sección 7 — Reviews explorer (`GET /metricas/reviews`)

**Estado:** ya implementado con BD; métricas no reemplazan este listado.

- [ ] Confirmar que filtros por sentimiento/tópico siguen siendo coherentes con datos cargados.
- [ ] (Opcional) enlazar desde KPIs/tópicos a queries del explorer con mismos períodos.

---

## Front Executive Dashboard (Next) — alineación con mocks

**Archivo de secciones:** `sources/app/olh-sentiment-ia/app/dashboard/page.tsx`  
**Mocks:** `sources/app/olh-sentiment-ia/lib/mock-data.ts`

Orden sugerido de sustitución de mocks por API (cuando el backend esté listo):

1. [ ] `HeroKpisSection` + `TrendChart` ← `kpis` + `sentimiento-mensual`
2. [ ] `CategoryGrid` ← `topicos`
3. [ ] Bloques derivados (insights, pain index, risk summary) ← composición de `topicos` + `alertas` + `kpis` (ajustar mapeo de tipos si hace falta)
4. [ ] `DataStrengthSection`, `AdvancedMetricsSection`, etc. ← valorar extensión de contrato o tablas derivadas si faltan campos

---

## Orden global de implementación en backend (vertical slices)

1. [ ] Fase 0
2. [ ] Sección 1 (KPIs globales)
3. [ ] Sección 2 (serie mensual)
4. [ ] Sección 3 (tópicos mensuales)
5. [ ] Sección 4 (top 5)
6. [ ] Sección 6 (alertas)
7. [ ] Sección 5 (detalle tópico + fragmentos)
8. [ ] Front: sección por sección según tabla anterior

---

## Notas para usar este archivo como *input* en el IDE

- Pegar o `@`-referenciar `planMetricas.md` al pedir implementación de una fase concreta.
- Marcar casillas `[ ]` → `[x]` en el repo a medida que se completen (commit opcional como bitácora).
- Si cambia el DDL o OpenAPI, actualizar la tabla **Referencias rápidas** y la fase afectada.
