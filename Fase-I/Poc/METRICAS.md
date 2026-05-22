# Métricas del Dashboard – POC Análisis de Sentimiento de Reviews

> Dashboard ejecutivo para el análisis de sentimiento de reseñas hoteleras.  
> Implementación: SPA estática (`index.html` + `app.js` + `styles.css`) usando **Chart.js**.

---

## KPIs Principales

Tres tarjetas en la parte superior del dashboard:

| KPI | Descripción | Origen |
|-----|-------------|--------|
| **Sentimiento promedio** | Porcentaje general de sentimiento positivo (ej. `72%`, tendencia `↑ 4.2%`) | Serie mensual `SENTIMENT_MENSUAL` en `app.js`; tendencia estática en HTML |
| **Reviews analizadas** | Conteo total de reseñas procesadas (ej. `1,247`) | Placeholder estático en HTML (no calculado en JS) |
| **Tópicos con alerta** | Cantidad de tópicos que superan el umbral de atención | Calculado dinámicamente: cuenta tópicos con `alerta: true` en `app.js` |

---

## Gráfico Principal

### Sentimiento promedio (%) en el tiempo

- Serie mensual de **12 meses** (`SENTIMENT_MENSUAL`)
- Filtrable por rangos: **Últimos 3 meses / 6 meses / 12 meses** o fechas personalizadas (Desde / Hasta)
- El **tooltip** de cada punto desglosa el score por tópico en ese mes (usando `TOPICOS_POR_MES`)

---

## Métricas por Tópico

Cada tópico expone tres métricas individuales, visibles en tarjetas, tabla, Top 5 y modal de detalle:

| Métrica | Descripción | Umbral / Lógica |
|---------|-------------|-----------------|
| **Score de sentimiento (%)** | Valor de sentimiento del tópico | ≥ 70% → positivo · ≥ 55% → advertencia · < 55% → negativo |
| **Cambio % vs período anterior** | Variación respecto al período previo | Positivo → `↑` (verde) · Negativo → `↓` (rojo) |
| **Estado de alerta** | Bandera que indica si el tópico requiere atención | Campo booleano `alerta` en los datos de ejemplo |

---

## Secciones del Dashboard

### Top 5 Tópicos
Los **5 tópicos con menor score** (los más críticos), ordenados de menor a mayor, mostrados en lista lateral. Cada ítem incluye badge de alerta si corresponde. Al hacer clic abre el **modal de detalle**.

### Tabla de Rendimiento
Todos los tópicos en formato tabular con:
- Nombre del tópico
- Score (%)
- Cambio % vs anterior
- Ícono de tendencia (`↑` / `↓`) con color UX

### Modal de Detalle
Al seleccionar un tópico (desde tarjeta o Top 5), muestra:
- Score individual
- Cambio %
- Mensaje "Requiere atención" si tiene alerta activa

---

## Tópicos Monitoreados

| Tópico | Estado en datos de ejemplo |
|--------|---------------------------|
| Limpieza | Sin alerta |
| Atención al cliente | Sin alerta |
| Instalaciones y servicios | **Con alerta** |
| Relación calidad-precio | **Con alerta** |
| Ruido | **Con alerta** |
| WiFi | **Con alerta** |
| Comodidad | Sin alerta |
| Desayuno / Gastronomía | Sin alerta |

---

## Umbrales Visuales

```
Score ≥ 70%  → Positivo   (verde)
Score ≥ 55%  → Advertencia (ámbar)
Score < 55%  → Negativo   (rojo)
```

---

## Notas de Integración Futura

- Sustituir datos estáticos por llamadas a la API o base de datos del modelo NLP.
- Conectar filtros de fechas al backend para filtrar por rango real.
- Sincronizar los KPIs de "Sentimiento promedio" y "Reviews analizadas" con los datos calculados.
- Ajustar tópicos y umbrales de alerta según los resultados del modelo de la tesis.
