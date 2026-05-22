# Cálculo detallado de métricas (MetricProcessor)

Este documento describe **cómo se calcula cada métrica** del pipeline mensual del servicio **MetricProcessor**, alineado con el DDL (`guidelines/ddl_bd.sql`), las reglas puras (`sources/apis/MetricProcessor/services/metricas_reglas.py`) y el repositorio SQL (`sources/apis/MetricProcessor/repositories/metricas_repository.py`).

---

## 1. Alcance y unidad de análisis

### 1.1 Unidad de agregación

Todas las métricas pre-calculadas se agrupan por:

- **`hotel_id`**
- **Mes natural** `(anio, mes)` según el campo `reviews.fecha_review` (año y mes calendario de la review, no la fecha de carga del archivo).

Un mismo archivo puede aportar reviews a **varios meses**. El job `POST /api/v1/metricas/calcular` recorre **cada mes distinto** presente en las fechas del archivo y ejecuta un ciclo completo de cálculo y persistencia por cada uno.

### 1.2 Qué reviews entran en los conteos

Para **métricas globales** y **métricas por tópico** (conteos y scores persistidos), solo se consideran reviews que cumplen:

- `reviews.hotel_id` = hotel del archivo procesado.
- `EXTRACT(YEAR/MONTH FROM fecha_review)` coincide con el período calculado.
- El archivo asociado (`log_archivos`) está en estado **`topics_identified`** o **`completed`**.

Así, si varios archivos del mismo hotel comparten un mes, el **UPSERT** refleja el **conjunto unificado** del hotel en ese mes, no solo el archivo que disparó el job.

### 1.3 Sentimiento de la review (nivel global)

El sentimiento por review proviene de **`predicciones_sentimiento`** unida a `reviews` (`predicciones_sentimiento.sentimiento`: `positivo`, `negativo`, `neutro`).

### 1.4 Sentimiento por mención de tópico

A nivel tópico se cuentan filas en **`review_topicos`**, cada una con su **`sentimiento`** propio (positivo / negativo / neutro) para esa mención.

> **Nota conceptual:** una misma review puede generar **varias menciones** (varias filas en `review_topicos`) si se detectan varios tópicos o varias unidades analizadas. Por eso el **score global** se basa en **reviews**, y el **score por tópico** en **menciones**.

---

## 2. Métricas globales mensuales (`metricas_globales_mensual`)

### 2.1 Conteos base

| Campo | Definición |
|--------|------------|
| `total_reviews` | Número de reviews del hotel en el mes que cumplen los filtros de §1.2. |
| `reviews_positivas` | Reviews con `predicciones_sentimiento.sentimiento = 'positivo'`. |
| `reviews_negativas` | Idem para `'negativo'`. |
| `reviews_neutras` | Idem para `'neutro'`. |

**Ejemplo:** En enero 2026 el hotel tiene 200 reviews elegibles: 120 positivas, 50 negativas, 30 neutras.

- `total_reviews = 200`
- `reviews_positivas = 120`, `reviews_negativas = 50`, `reviews_neutras = 30`

### 2.2 `score_promedio` (score global / sentimiento global)

**Fórmula (código — suavizado bayesiano):**

\[
\text{score\_promedio} = \frac{\text{reviews\_positivas} + C \cdot m}{\text{total\_reviews} + C} \times 100
\]

- **`m`** ∈ [0, 1] y **`C`** ≥ 0: prior del corpus (equivalente a añadir `C·m` pseudo-positivas y `C(1-m)` pseudo-no-positivas antes de dividir). Se configuran en MetricProcessor con **`LAPLACE_PRIOR_M`** (default `0.6`) y **`LAPLACE_PRIOR_C`** (default `5`). Con **`C = 0`** se obtiene la proporción bruta \((\text{reviews\_positivas}/\text{total\_reviews})\times 100\).
- Resultado tipo **porcentaje** (en la práctica acotado por `NUMERIC(5,2)` en BD).
- **Redondeo:** 2 decimales, **half up** (`ROUND_HALF_UP`), en `calcular_score_global` → `_score_bayesiano`.

**Casos límite:**

- Si `total_reviews = 0`, se guarda **`0.00`** (evita meses vacíos inflados hacia el prior; respeta `NOT NULL`).

**Ejemplos numéricos** (por defecto `m = 0.6`, `C = 5` → se suman 3 pseudo-positivas y el denominador aumenta en 5):

- `reviews_positivas = 980`, `total_reviews = 1432` → \((980+3)/(1432+5)\times 100 \approx\) **`68.41`**
- `1` positiva de `3` reviews → \((1+3)/(3+5)\times 100 = 50.00\) → **`50.00`**

### 2.3 `cambio_pct_vs_anterior`

En la implementación actual, este valor es la **diferencia en puntos porcentuales** entre el score del mes actual y el **`score_promedio`** del **mes calendario inmediatamente anterior** del mismo hotel (consulta a `metricas_globales_mensual`).

\[
\text{cambio\_pct\_vs\_anterior} = \text{score\_mes actual} - \text{score\_mes anterior}
\]

- Si **no existe** fila del mes anterior → el campo es **`NULL`** (primer mes con datos para ese hotel).
- Redondeo a **2 decimales** (half up).

**Ejemplo:**

- Mes anterior: `score_promedio = 65.80`
- Mes actual: `score_promedio = 68.40`
- `cambio_pct_vs_anterior = 68.40 - 65.80 = +2.60` (subieron 2.6 puntos, no un “+2.6 %” sobre 65.8).

> El nombre de columna sugiere “porcentaje de cambio”, pero el **código** implementa **delta absoluta** del score. Conviene interpretar el KPI como **variación del índice de positividad** en puntos.

### 2.4 `total_alertas`

No es un conteo SQL independiente: en el job, tras evaluar todos los tópicos del mes, se define como:

\[
\text{total\_alertas} = \text{número de tópicos en ese mes con } \text{alerta activa} \text{ (ver §4)}
\]

Es decir, coincide con la cantidad de tópicos que en ese período cumplen `score_promedio < umbral_alerta` **y** para los que se insertó una fila en `alertas` en esa pasada (tras borrar alertas no resueltas del período; ver §5).

---

## 3. Métricas por tópico mensuales (`metricas_topico_mensual`)

Solo se generan filas para **tópicos con actividad** en el mes: el agregado SQL agrupa por `topico_id` y exige al menos una mención (`COUNT(*)` en `review_topicos`).

### 3.1 Conteos base

| Campo | Definición |
|--------|------------|
| `total_menciones` | Filas en `review_topicos` para ese `topico_id`, hotel y mes (mismos filtros de archivo §1.2). |
| `menciones_positivas` | Menciones con `review_topicos.sentimiento = 'positivo'`. |
| `menciones_negativas` | Idem `'negativo'`. |
| `menciones_neutras` | Idem `'neutro'`. |

**Ejemplo:** Tópico “Limpieza” en febrero 2026: 80 menciones totales → 30 positivas, 40 negativas, 10 neutras.

### 3.2 `score_promedio` (score por tópico)

**Fórmula:**

\[
\text{score\_promedio} = \frac{\text{menciones\_positivas} + C \cdot m}{\text{total\_menciones} + C} \times 100
\]

Los mismos **`m`** y **`C`** que en §2.2 (`LAPLACE_PRIOR_M`, `LAPLACE_PRIOR_C` en MetricProcessor). Redondeo a **2 decimales** (half up).

**Ejemplos (defaults `m=0.6`, `C=5`):** 200 positivas / 310 menciones → **`64.44`**.  
Dos positivas de tres menciones → \((2+3)/(3+5)\times 100\) → **`62.50`**.

**Caso límite:** `total_menciones = 0` → score **`0.00`** (no debería ocurrir en filas persistidas con actividad, pero la función lo define por seguridad).

### 3.3 `cambio_pct_vs_anterior`

Igual criterio que el global: **diferencia** entre el score del tópico en el mes actual y el `score_promedio` del **mismo tópico** en el **mes calendario anterior** (`metricas_topico_mensual`). Si no hay mes anterior → `NULL`.

**Ejemplo:** Score tópico pasó de `65.00` a `60.00` → **`-5.00`**.

### 3.4 `alerta` (booleano en la tabla de métricas)

\[
\text{alerta} = \begin{cases}
\text{TRUE} & \text{si } \text{score\_promedio} < \text{topicos.umbral\_alerta} \\
\text{FALSE} & \text{en caso contrario}
\end{cases}
\]

- Comparación **estricta**: si el score es **igual** al umbral, **no** hay alerta (`65.00` vs umbral `65` → sin alerta).
- Si `umbral_alerta` es `NULL` en catálogo, el job **no** marca alerta para ese tópico.

**Ejemplo:** `score_promedio = 52.30`, `umbral_alerta = 65` → `alerta = TRUE`.

---

## 4. Tabla `alertas` (eventos de negocio)

Cuando para un tópico `alerta = TRUE` en el upsert de métricas:

1. Se inserta una fila en **`alertas`** con `score_actual`, `umbral_usado` y un `mensaje` generado (texto tipo: score X% bajo umbral Y%).
2. Antes, en el mismo período, se ejecutó **`DELETE`** de alertas con `resuelta = FALSE` para ese `(hotel_id, anio, mes)` para evitar duplicados obsoletos. Las alertas **resueltas** no se eliminan.

Las lecturas del dashboard sobre “alertas activas” se apoyan en este historial y en el flag `resuelta`.

---

## 5. Métricas derivadas solo en lectura (API / presentación)

Estos valores **no se guardan** como columnas nuevas en el DDL; se calculan al armar la respuesta JSON.

### 5.1 `GET /api/v1/metricas/kpis`

- **`sentimiento_promedio.score`:** copia de `metricas_globales_mensual.score_promedio`.
- **`sentimiento_promedio.cambio_pct`:** copia de `cambio_pct_vs_anterior`; si es `NULL`, en KPI se expone como **`0.0`**.
- **`sentimiento_promedio.tendencia`:** derivada con `tendencia_desde_cambio_pct`:
  - `NULL` → `"stable"`
  - valor `> 0` → `"up"`
  - valor `< 0` → `"down"`
  - `0` → `"stable"`
- **`reviews_analizadas`:** `total_reviews` global del mes.
- **`topicos_con_alerta`:** `total_alertas` del mes (conteo de tópicos bajo umbral en esa corrida).

### 5.2 `GET /api/v1/metricas/sentimiento-mensual`

Serie de puntos leídos de `metricas_globales_mensual` en un rango de meses: cada punto incluye `anio`, `mes`, `score_promedio`, `total_reviews`. **No** recalcula scores; solo **lee** filas ya materializadas.

El rango por defecto (“últimos N meses”) se resuelve en código a partir de la fecha del servidor (`date.today()`).

### 5.3 `GET /api/v1/metricas/topicos`

Por cada fila de `metricas_topico_mensual` (con metadatos de `topicos`), se añade **`tendencia`** con la misma regla de §5.1 a partir de `cambio_pct_vs_anterior`.

### 5.4 `GET /api/v1/metricas/topicos/top5`

Selección de hasta **5** tópicos con `total_menciones > 0`, ordenados por **`score_promedio` ascendente** (peor sentimiento primero); desempate por `t.id`. La **`posicion`** en JSON es 1-based según ese orden.

### 5.5 `GET /api/v1/metricas/topicos/<slug>/detalle`

- Números agregados: mismos campos que `metricas_topico_mensual` + `umbral_alerta` del catálogo.
- **`fragmentos_destacados`:** hasta 3 textos desde `review_topicos` del slug y mes, con `fragmento` no vacío, ordenados por:
  1. Sentimiento: **negativo** primero, luego neutro, luego positivo.
  2. Mayor **`score_topico`** (expuesto como `confianza`).
  3. `rt.id DESC` como desempate.

> Los fragmentos **no** aplican en la consulta el mismo filtro de estado de `log_archivos` que los agregados mensuales; usan `hotel_id`, slug y fecha de review. Si hiciera falta alinear criterios, habría que cambiar explícitamente esa consulta en el repositorio.

---

## 6. Resumen de fórmulas

| Métrica | Fórmula principal |
|--------|-------------------|
| Score global | `((reviews_positivas + C·m) / (total_reviews + C)) × 100` |
| Score por tópico | `((menciones_positivas + C·m) / (total_menciones + C)) × 100` |
| Cambio vs mes anterior | `score_mes_actual - score_mes_anterior` (puntos; `NULL` si no hay anterior) |
| Alerta de tópico | `score_promedio < umbral_alerta` (estricto) |
| Tendencia (API) | signo del cambio vs anterior; `NULL` tratado como estable en listados |

**Re-score manual:** `POST /api/v1/metricas/recalcular` (MetricProcessor) reaplica las mismas fórmulas sobre los conteos ya persistidos en `metricas_globales_mensual` y `metricas_topico_mensual` para un `(hotel_id, anio, mes)`. Para coherencia de `cambio_pct_vs_anterior` en meses consecutivos, conviene ejecutar por orden cronológico.

---

## 7. Referencias en el repositorio

| Tema | Ubicación |
|------|-----------|
| Reglas puras y redondeos | `sources/apis/MetricProcessor/services/metricas_reglas.py` |
| Orquestación del job, KPIs y `/recalcular` | `sources/apis/MetricProcessor/services/metricas_service.py` |
| SQL de conteos y lecturas | `sources/apis/MetricProcessor/repositories/metricas_repository.py` |
| Contrato y endpoints | `guidelines/api-contracts.md`, `guidelines/openapi.json` |
| Plan de producto / fases | `sources/apis/MetricProcessor/planMetricas.md` |
