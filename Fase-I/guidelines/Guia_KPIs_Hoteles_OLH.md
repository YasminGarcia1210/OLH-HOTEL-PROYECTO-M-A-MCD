# Guía de KPIs — Hoteles OLH · Sentiment Intelligence

> **Proyecto:** POC Tesis ICESI  
> **Objetivo:** Documentar y explicar cada KPI del dashboard de análisis de sentimiento para hoteles.  
> **Fecha:** Abril 2026

---

## ¿Qué es un KPI?

Un **KPI** (Key Performance Indicator) es un **indicador clave de rendimiento**: una métrica cuantificable que permite evaluar el desempeño de un aspecto específico del negocio en relación con objetivos establecidos.

En el contexto de este proyecto, cada KPI mide la **percepción de los huéspedes** respecto a diferentes aspectos del hotel, a partir del análisis de reseñas mediante un modelo de NLP (Procesamiento de Lenguaje Natural).

---

## 1. KPIs de Sentimiento — Core del Modelo

Estos indicadores constituyen el núcleo del sistema, ya que miden directamente la percepción del huésped a partir del contenido de las reseñas analizadas.

### 1.1 Customer Sentiment Score (Sentimiento Promedio)

- **Valor actual:** 72%
- **¿Qué mide?** La percepción **global** de los huéspedes sobre el hotel, calculada como el promedio del sentimiento de **todas** las reseñas analizadas.
- **¿Cómo se calcula?** El modelo de NLP analiza cada reseña y le asigna un porcentaje de sentimiento (0% = muy negativo, 100% = muy positivo). Este KPI corresponde al **promedio** de todos esos valores.
- **¿Por qué importa?** Es el **indicador general** del hotel. Una disminución en este valor señala áreas de atención; un incremento indica que las mejoras implementadas están generando resultados.
- **Escala de interpretación:**
  - **80–100%:** Excelente — los huéspedes expresan alta satisfacción.
  - **70–79%:** Bueno — existen oportunidades de mejora identificables.
  - **60–69%:** Regular — se requieren acciones correctivas.
  - **Menos de 60%:** Crítico — existen problemas significativos que atender.

### 1.2 Variación del Sentimiento (Δ%)

- **Valor actual:** +1.42%
- **¿Qué mide?** La **diferencia** entre el sentimiento del período actual y el período anterior, indicando si la tendencia es positiva o negativa.
- **¿Cómo se calcula?** `Δ% = Sentimiento actual − Sentimiento anterior`
- **¿Por qué importa?** El sentimiento promedio refleja el estado presente del indicador, mientras que la variación revela la **dirección de la tendencia**. Un hotel con 72% en ascenso representa una situación distinta a uno con el mismo valor en descenso.
- **Interpretación:**
  - **Positivo (▲):** El hotel está **mejorando** — las acciones implementadas están dando resultado.
  - **Negativo (▼):** El hotel está **deteriorándose** — se requiere identificar los factores causantes.
  - **Cercano a 0:** Estabilidad — no se registran cambios significativos.

### 1.3 Tendencia del Sentimiento en el Tiempo

- **Visualización:** Gráfica de línea (May 2025 → Abr 2026)
- **¿Qué mide?** El **comportamiento mensual** del sentimiento promedio a lo largo del tiempo, presentado como una serie temporal.
- **¿Cómo se construye?** Se calcula el sentimiento promedio de cada mes por separado y se representan los valores conectados en una línea continua.
- **¿Por qué importa?** Esta gráfica tiene valor estratégico porque permite:
  - Detectar **temporadas de bajo rendimiento** (por ejemplo, períodos de alta demanda con menor calidad percibida).
  - Medir el **impacto de intervenciones** (por ejemplo, renovaciones o cambios en el servicio).
  - Identificar **tendencias sostenidas** a largo plazo.
- **Interpretación:**
  - **Línea ascendente:** Tendencia positiva — mejora continua en la percepción.
  - **Línea descendente:** Tendencia negativa — deterioro progresivo en la experiencia.
  - **Picos y valles:** Presencia de eventos o temporadas que afectan la percepción de los huéspedes.

### 1.4 Mejor y Peor Área

- **Mejor:** Ubicación (88%)
- **Peor:** Ruido (58%)
- **¿Qué mide?** De todas las categorías analizadas, identifica la que presenta el sentimiento **más alto** y la que presenta el sentimiento **más bajo**.
- **¿Por qué importa?** Proporciona una respuesta inmediata sobre cuál es la principal fortaleza y cuál es el mayor punto de mejora del hotel, sin necesidad de revisar el detalle completo del dashboard.

---

## 2. KPIs de Volumen — Data Strength

Estos indicadores no miden sentimiento, sino el **volumen y calidad de los datos** disponibles para el modelo. Son relevantes porque determinan la **confiabilidad estadística** de los demás KPIs.

### 2.1 Reviews Analizadas (Total)

- **Valor actual:** 1,247
- **¿Qué mide?** La cantidad **total** de reseñas procesadas por el modelo.
- **¿Por qué importa?** En términos estadísticos, a mayor volumen de datos, mayor es la confiabilidad del análisis. Con un número reducido de reseñas, opiniones extremas pueden distorsionar los promedios. Con 1,247 registros, los resultados son significativamente más estables y representativos.
- **Escala de interpretación:**
  - **Menos de 100:** Precaución — los resultados pueden no ser representativos.
  - **100–500:** Aceptable — los resultados son utilizables con reservas.
  - **500–1000:** Bueno — los KPIs presentan confiabilidad adecuada.
  - **Más de 1000:** Excelente — alta confiabilidad estadística.

### 2.2 Reviews por Mes (Promedio)

- **Valor actual:** 104 reviews/mes
- **¿Qué mide?** El **flujo promedio mensual** de reseñas recibidas.
- **¿Cómo se calcula?** Total de reseñas ÷ número de meses del período analizado.
- **¿Por qué importa?** Un volumen mensual bajo puede comprometer la confiabilidad del sentimiento calculado para ese período. Este indicador permite verificar si el flujo de datos es constante y suficiente.

### 2.3 Fuentes de Datos

- **Valor actual:** 4 fuentes (Google, Booking, TripAdvisor, Expedia)
- **¿Qué mide?** El número de **plataformas digitales** desde las cuales se extraen reseñas.
- **¿Por qué importa?** El análisis basado en una sola fuente puede presentar sesgos de selección (por ejemplo, ciertos perfiles de huéspedes concentran sus comentarios en plataformas específicas). La integración de múltiples fuentes incrementa la representatividad del análisis.

### 2.4 Confiabilidad del Modelo

- **Valor actual:** Alta
- **¿Qué mide?** Un indicador cualitativo que refleja la confiabilidad del modelo en función del volumen de datos disponibles.
- **¿Cómo se determina?** Con base en el número total de reseñas:
  - n > 1,000 → Alta
  - n entre 500–1,000 → Media
  - n < 500 → Baja

---

## 3. KPIs de Riesgo / Alertas

Estos indicadores señalan las áreas que requieren atención prioritaria, permitiendo al equipo directivo identificar con rapidez dónde concentrar las acciones correctivas.

### 3.1 Tópicos en Alerta

- **Valor actual:** 4
- **¿Qué mide?** La cantidad de categorías (tópicos) cuyo sentimiento se encuentra **por debajo del umbral definido** (en este caso, 65%).
- **¿Por qué importa?** Un sentimiento general de 72% puede enmascarar problemas puntuales. Este indicador revela **cuántas áreas específicas presentan niveles críticos** que requieren intervención, independientemente del promedio general.
- **Tópicos actualmente en alerta:**
  - Ruido → 58% (Crítico)
  - WiFi → 61% (Crítico)
  - Relación Calidad-Precio → 65% (Alerta)
  - Instalaciones → 70% (Alerta — próximo al umbral)

### 3.2 Porcentaje de Tópicos Críticos

- **Valor actual:** 36% (4 de 11 tópicos)
- **¿Qué mide?** La proporción del total de tópicos analizados que se encuentra por debajo del umbral.
- **¿Cómo se calcula?** `(Tópicos en alerta ÷ Total de tópicos) × 100`
- **¿Por qué importa?** Un único tópico con bajo rendimiento (9%) sugiere un problema aislado. Cuatro tópicos críticos (36%) indican un **problema sistémico** que puede requerir intervenciones más profundas en múltiples áreas.

### 3.3 Alertas Nuevas (últimos 7 días)

- **Valor actual:** 2
- **¿Qué mide?** La cantidad de tópicos que **cruzaron el umbral hacia abajo** durante la última semana.
- **¿Por qué importa?** Permite detectar **deterioros recientes** de manera oportuna. Una caída repentina en un tópico que previamente se mantenía estable puede indicar un evento o cambio operativo que merece investigación inmediata.

### 3.4 Umbral de Riesgo Reputacional (Donut Chart)

- **Visualización:** Gráfica de dona (64% OK vs 36% Crítico)
- **¿Qué mide?** La proporción visual entre tópicos en niveles saludables y tópicos en zona de riesgo.
- **¿Por qué importa?** Permite comunicar de forma **visual e inmediata** el nivel de riesgo reputacional del hotel. Esta visualización facilita la comprensión del estado general sin necesidad de analizar cifras individuales.

---

## 4. KPIs por Categoría — Score y Variación

Esta sección presenta el análisis más granular del sistema, detallando el desempeño de cada área del hotel de forma individual.

### 4.1 Score por Categoría

Cada categoría presenta su propio porcentaje de sentimiento, calculado a partir de los fragmentos de reseñas clasificados por el modelo:

| Categoría | Score | Estado | Interpretación |
|---|---|---|---|
| Ubicación | 88% | Excelente | Los huéspedes valoran positivamente la ubicación del hotel |
| Atención del Personal | 82% | Muy bueno | El servicio al cliente representa una fortaleza del establecimiento |
| Piscina / Zona Común | 80% | Muy bueno | Las áreas comunes generan una percepción favorable |
| Confort Habitación | 78% | Bueno | Las habitaciones son adecuadas, con margen de mejora |
| Limpieza | 75% | Bueno | Nivel aceptable, con oportunidades de optimización |
| Alimentación | 74% | Bueno | La oferta gastronómica cumple las expectativas básicas |
| Estacionamiento | 72% | Aceptable | Funcional, sin constituir un diferenciador positivo |
| Instalaciones y Servicios | 70% | Atención | Valor próximo al umbral de alerta |
| Relación Calidad-Precio | 65% | Alerta | Los huéspedes perciben que el costo no se corresponde con el valor recibido |
| WiFi | 61% | Crítico | Problema recurrente en las reseñas negativas |
| Ruido | 58% | Crítico | Principal fuente de insatisfacción reportada |

- **¿Cómo se calcula cada uno?** El modelo de NLP clasifica cada fragmento de una reseña por tópico. Por ejemplo, ante la expresión "la ubicación era perfecta pero el WiFi era terrible", el modelo asigna sentimiento positivo a "Ubicación" y negativo a "WiFi". El score de cada categoría corresponde al promedio de todos los sentimientos clasificados bajo ese tópico.

### 4.2 Variación por Categoría

Cada categoría también refleja su **cambio respecto al período anterior**:

| Categoría | Variación | Indicación |
|---|---|---|
| Ruido | -5.2% | Deterioro acelerado — problema en crecimiento |
| Relación Calidad-Precio | -4.2% | Deterioro significativo |
| Instalaciones | -3.0% | Tendencia descendente |
| WiFi | -2.0% | Deterioro moderado |
| Limpieza | -1.2% | Leve descenso |
| Ubicación | +0.5% | Estable |
| Estacionamiento | +1.0% | Leve mejora |
| Alimentación | +1.8% | Mejora sostenida |
| Atención del Personal | +2.1% | Tendencia positiva |
| Confort Habitación | +2.4% | Mejora consistente |
| Piscina / Zona Común | +3.2% | Mayor incremento del período |

- **¿Por qué importa?** Este indicador es de **alto valor estratégico para la toma de decisiones operativas**, ya que permite identificar con precisión las áreas donde concentrar recursos. Una caída de -5.2% en Ruido, por ejemplo, justifica una investigación específica sobre posibles causas (obras cercanas, eventos, deficiencias en aislamiento acústico).

---

## 5. KPIs de Ranking — Top Insights

Estos indicadores organizan la información en **rankings comparativos** para facilitar la priorización en la toma de decisiones.

### 5.1 Top Fortalezas (Strengths)

Las **4 categorías con mayor sentimiento positivo**:

1. **Ubicación** → 88%
2. **Atención del Personal** → 82%
3. **Piscina / Zona Común** → 80%
4. **Confort Habitación** → 78%

- **¿Por qué importa?** Estas áreas representan las **ventajas competitivas** del establecimiento. Desde el ámbito de marketing, pueden destacarse en la comunicación con clientes potenciales. Desde operaciones, deben protegerse para evitar su deterioro.

### 5.2 Top Pain Points (Áreas Críticas)

Las **4 categorías con menor sentimiento**:

1. **Ruido** → 58%
2. **WiFi** → 61%
3. **Relación Calidad-Precio** → 65%
4. **Instalaciones** → 70%

- **¿Por qué importa?** Estas áreas representan las **principales brechas de experiencia** del establecimiento. Son las que los huéspedes mencionan con mayor frecuencia en tono negativo y las que mayor impacto tienen en la reputación digital del hotel.

---

## 6. KPIs de Problemas Específicos — Pain Points Index

Esta sección profundiza en los tópicos que aparecen de forma recurrente en las reseñas negativas, complementando el análisis de las categorías principales.

### 6.1 Score de cada Pain Point

| Tópico | Score | Estado | Acción sugerida |
|---|---|---|---|
| Ruido | 58% | Crítico | Identificar fuentes de ruido; evaluar mejoras en aislamiento acústico |
| WiFi | 61% | Crítico | Modernizar infraestructura de red; incrementar ancho de banda disponible |
| Estacionamiento | 72% | Estable | Monitorear periódicamente; no requiere acción urgente |
| Piscina / Zona Común | 80% | Favorable | Mantener el estándar operativo actual |

### 6.2 Porcentaje de Tópicos Bajo Umbral

- **Valor actual:** 36% de los tópicos se encuentran por debajo del 65%
- **¿Qué mide?** La proporción del total de tópicos analizados que se encuentra en zona de riesgo.
- **¿Cómo se calcula?** Se establece un **umbral** (en este caso 65%) y se determina cuántos tópicos se encuentran por debajo de dicho valor.
- **¿Por qué importa?** Un incremento sostenido de este porcentaje a lo largo del tiempo indica que el hotel presenta cada vez **más áreas problemáticas**, lo que constituye una señal de alerta sobre la experiencia general del huésped.

---

## 7. KPIs Ejecutivos — Resumen para Presentación

Los siguientes son los **6 indicadores esenciales** recomendados para una presentación directiva o ejecutiva. Ofrecen una lectura concisa y completa del estado del hotel:

| KPI | Valor | Interpretación |
|---|---|---|
| **Customer Sentiment Score** | 72% | Percepción global del huésped |
| **Experience Trend** | +1.42% | El hotel presenta una tendencia positiva |
| **Tópicos Críticos** | 4 | Áreas que requieren atención prioritaria |
| **Peor Categoría** | 65% (Calidad-Precio) | Principal oportunidad de mejora |
| **Mejor Categoría** | 88% (Ubicación) | Principal fortaleza del establecimiento |
| **Main Complaint** | 58% (Ruido) | Queja más frecuente en las reseñas |

- **¿Por qué estos 6?** Porque responden las preguntas esenciales que cualquier directivo plantearía:
  1. ¿Cuál es el estado general del hotel? → 72%
  2. ¿El hotel está mejorando o deteriorándose? → Mejorando (+1.42%)
  3. ¿Existen problemas identificados? → Sí, 4 tópicos críticos
  4. ¿Cuál es el área de mayor preocupación? → Calidad-Precio (65%)
  5. ¿Cuál es la principal fortaleza? → Ubicación (88%)
  6. ¿Cuál es la queja predominante? → Ruido (58%)

---

## Resumen: Flujo de Análisis

```
┌─────────────────────────────────────────────────┐
│           CUSTOMER EXPERIENCE INDEX              │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │Sentimiento│  │Variación │  │  Tendencia   │   │
│  │  72%      │  │ +1.42%   │  │  ↗ Subiendo  │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                     │                            │
│         ┌───────────┴───────────┐                │
│         ▼                       ▼                │
│  ┌─────────────┐    ┌──────────────────┐         │
│  │ Fortalezas  │    │  Áreas Críticas  │         │
│  │ Ubicación   │    │ Ruido (58%)      │         │
│  │ Personal    │    │ WiFi (61%)       │         │
│  │ Piscina     │    │ Cal-Precio (65%) │         │
│  └─────────────┘    └──────────────────┘         │
│                          │                       │
│                          ▼                       │
│                  ┌───────────────┐               │
│                  │   4 Alertas   │               │
│                  │   Activas     │               │
│                  └───────────────┘               │
│                          │                       │
│                          ▼                       │
│              ┌──────────────────────┐            │
│              │  Resumen Ejecutivo   │            │
│              │  Sentimiento: 72%    │            │
│              │  Tendencia: +1.42%   │            │
│              │  Tópicos críticos: 4 │            │
│              │  Ruido: 58%          │            │
│              └──────────────────────┘            │
└─────────────────────────────────────────────────┘
```

**Flujo de análisis:**
1. **Medición** del sentimiento general → ¿Cuál es el estado actual?
2. **Seguimiento** de la variación y tendencia → ¿Hacia dónde se dirige el indicador?
3. **Desglose** por categoría → ¿Qué áreas funcionan correctamente y cuáles presentan problemas?
4. **Identificación** de alertas y áreas críticas → ¿Qué requiere intervención prioritaria?

---

## Notas Finales

- Todos los datos presentados en el dashboard son **simulados** para la prueba de concepto (POC).
- Los umbrales definidos (como el 65% para alertas) son **configurables** según los criterios del establecimiento hotelero.
- El sistema está diseñado para **escalar**: puede aplicarse a múltiples propiedades y permitir comparaciones entre hoteles de la misma cadena.

---

*Documento elaborado para el proyecto de tesis ICESI · Hoteles OLH · Sentiment Intelligence*
