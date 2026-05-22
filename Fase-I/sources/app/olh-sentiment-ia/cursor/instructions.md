# Objetivo del Proyecto

Crear una aplicación web de inteligencia de sentimientos para **Hoteles OLH**, llamada **Sentiment AI Intelligence Suite**, usando **NextJS (App Router)** y **Tailwind CSS**.

El proyecto ya está creado y con Tailwind instalado, pero sin estilos ni funcionalidades. El objetivo es implementar el diseño y las funcionalidades básicas de una plataforma de métricas hoteleras basada en análisis de sentimientos y tópicos, moderna, oscura y de carácter editorial-premium, siguiendo exactamente los diseños presentados en las referencias que serán proporcionadas.

---

## Identidad Visual: "The Nocturnal Intelligence"

Esta no es una app de dashboard genérica. Es una experiencia editorial de alto nivel dirigida a tomadores de decisiones de Hoteles OLH. La estética es la de un lounge de lujo a medianoche: sofisticada, enfocada, premium.

### Sistema de Color (Tailwind custom tokens)

Configurar estos tokens en `tailwind.config.ts`:

```ts
colors: {
  "primary": "#D4A847",
  "primary-container": "#d4a847",
  "primary-fixed": "#ffdea0",
  "primary-fixed-dim": "#eec05c",
  "on-primary": "#402d00",
  "on-primary-fixed": "#261a00",
  "on-primary-fixed-variant": "#5c4300",
  "on-primary-container": "#563e00",
  "inverse-primary": "#795900",
  "secondary": "#bcc7de",
  "secondary-container": "#3e495d",
  "secondary-fixed": "#d8e3fb",
  "secondary-fixed-dim": "#bcc7de",
  "on-secondary": "#263143",
  "on-secondary-container": "#aeb9d0",
  "on-secondary-fixed": "#111c2d",
  "on-secondary-fixed-variant": "#3c475a",
  "tertiary": "#52e2a6",
  "tertiary-container": "#2bc58c",
  "tertiary-fixed": "#6ffbbe",
  "tertiary-fixed-dim": "#4edea3",
  "on-tertiary": "#003824",
  "on-tertiary-container": "#004c32",
  "on-tertiary-fixed": "#002113",
  "on-tertiary-fixed-variant": "#005236",
  "error": "#ffb4ab",
  "error-container": "#93000a",
  "on-error": "#690005",
  "on-error-container": "#ffdad6",
  "surface": "#11131b",
  "surface-dim": "#11131b",
  "surface-bright": "#373941",
  "surface-variant": "#32343d",
  "surface-container-lowest": "#0c0e15",
  "surface-container-low": "#191b23",
  "surface-container": "#1d1f27",
  "surface-container-high": "#272a32",
  "surface-container-highest": "#32343d",
  "surface-tint": "#D4A847",
  "background": "#11131b",
  "on-background": "#e1e2ed",
  "on-surface": "#e1e2ed",
  "on-surface-variant": "#d2c5b1",
  "outline": "#9a8f7d",
  "outline-variant": "#4e4637",
  "inverse-surface": "#e1e2ed",
  "inverse-on-surface": "#2e3038",
  "accent": "#D4A847",
}
```

### Tipografía

```ts
fontFamily: {
  headline: ["Noto Serif", "serif"],
  body: ["Manrope", "sans-serif"],
  label: ["Inter", "sans-serif"],
}
```

Importar en `layout.tsx` desde Google Fonts:
- `Noto Serif` (weights: 400, 700, italic)
- `Manrope` (weights: 400, 500, 700)
- `Inter` (weights: 400, 600)
- Material Symbols Outlined (para íconos)

### Border Radius

```ts
borderRadius: {
  DEFAULT: "0.125rem",
  lg: "0.25rem",
  xl: "0.5rem",
  full: "0.75rem",
  card: "14px",
  "card-sm": "10px",
}
```

### Reglas de Diseño Críticas

1. **Regla "Sin Líneas":** Nunca usar bordes `1px solid` para separar secciones. La separación se logra únicamente con cambios de color de fondo entre los tokens `surface-*`.
2. **Regla "Glass & Gradient":** Los elementos flotantes (modales, dropdowns) usan glassmorphism: `background: rgba(50, 52, 61, 0.4)` con `backdrop-blur` de 12px–20px.
3. **Gradient Gold:** Los CTAs principales usan `background: linear-gradient(135deg, #f2c35f 0%, #D4A847 100%)`.
4. **Sombras tipo glow:** `box-shadow: 0px 12px 32px rgba(225,226,237,0.04)`. Nunca sombras duras.
5. **Sin blanco puro:** Usar siempre `on-surface` (`#e1e2ed`) en lugar de `#FFFFFF`.

### Clases CSS Globales (en `globals.css`)

```css
.glass {
  background: rgba(50, 52, 61, 0.4);
  backdrop-filter: blur(16px);
}
.gradient-gold {
  background: linear-gradient(135deg, #f2c35f 0%, #D4A847 100%);
}
.section-divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.section-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, rgba(212, 168, 71, 0.25), transparent 60%);
}
.tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 3px 10px;
  border-radius: 100px;
  display: inline-block;
}
.tag-crit { background: rgba(255, 107, 107, 0.1); color: #FF6B6B; }
.tag-warn { background: rgba(255, 170, 92, 0.1); color: #FFAA5C; }
.tag-ok   { background: rgba(61, 220, 151, 0.1); color: #3DDC97; }
```

---

## Estructura de Rutas (App Router)

```
app/
├── layout.tsx                  → RootLayout con fuentes, clase "dark", sidebar y topbar
├── page.tsx                    → Redirige a /dashboard
├── (auth)/
│   └── register/
│       └── page.tsx            → Página de registro / login
├── dashboard/
│   └── page.tsx                → Executive Dashboard (vista principal de métricas)
├── upload/
│   └── page.tsx                → Carga y procesamiento de datos de reseñas
└── admin/
    └── page.tsx                → Administración del sistema
```

---

## Layout Principal (`app/layout.tsx`)

El layout envuelve todas las rutas autenticadas con:
- **Sidebar izquierda fija** (`w-64`, `bg-surface-container-lowest`)
- **TopBar sticky** (`h-16`, `bg-surface`, `border-b border-surface-variant/10`)
- **Área de contenido** con `md:ml-64`

### Sidebar — Navegación

Links con íconos de Material Symbols Outlined:

| Ícono | Label | Ruta |
|---|---|---|
| `dashboard` | Dashboard | `/dashboard` |
| `analytics` | Reviews | `/dashboard` (sección) |
| `cloud_upload` | Upload | `/upload` |
| `settings` | Settings | `/admin` |

- Link activo: texto `primary`, `bg-surface-container`, borde derecho `border-r-2 border-primary`
- Link inactivo: texto `on-surface/40`, hover `bg-surface hover:text-on-surface`
- CTA "New Analysis": botón `gradient-gold`, texto `on-primary`, uppercase, tracking-widest
- Al fondo: links de Support y Logout

### TopBar

- Izquierda: Logotipo "**Hoteles OLH**" (italic, `font-headline`, `text-primary`) + nav secundaria (Overview, Reports, Benchmarks)
- Derecha: Input de búsqueda (`bg-surface-container`, `border-b-2 border-outline-variant`) + ícono notificaciones + avatar de usuario

---

## Páginas

### 1. `/dashboard` — Executive Dashboard

Referencia visual: `stitch/executive_dashboard_original_template_style/`

Implementar las siguientes secciones en orden:

#### Sección 1: Hero KPIs — "Sentimiento General · Core del Modelo"

Grid de 12 columnas con 4 cards:

- **Card principal (col-span-5):** Score de sentimiento general (`72%`) en `text-7xl font-headline text-primary`. Fondo degradado oscuro azulado. Glow ambiental dorado en esquina superior derecha. Badge de variación positiva con estilo `bg-tertiary/10 text-tertiary`.
- **Card variación Δ% (col-span-2.5):** `+1.42%` en `text-4xl text-tertiary`. Subtexto descriptivo.
- **Card mejor área (col-span-2.5):** `88%` en `text-4xl text-tertiary`. Subtexto "📍 Ubicación".
- **Card peor área (col-span-2.5):** `58%` en `text-4xl text-error`. Subtexto "🔇 Ruido · Pain Point #1".

Todas las cards: `bg-surface-container rounded-card border border-white/5 p-6`.

#### Sección 2: Tendencia del Sentimiento

Gráfica de línea temporal (mensual) con Recharts o Chart.js. Card `bg-surface-container rounded-card p-8`. Incluir selector de período (3M / 6M / 1A) con tabs estilo ghost.

#### Sección 3: Análisis por Tópicos

Cards por cada categoría (Habitaciones, Servicio, Comida, Ubicación, Ruido, Limpieza) con:
- Score porcentual en `font-headline`
- Barra de progreso thin (sin bordes, usando color de fondo)
- Chip de sentimiento (`.tag-ok`, `.tag-warn`, `.tag-crit`)

#### Sección 4: Reseñas Recientes

Lista sin dividers. Separación visual de 16px entre ítems o alternancia sutil `surface-container` / `surface-container-low`. Cada ítem: avatar, texto de reseña truncado, chip de sentimiento, fecha. Botón "Ver todas" ghost con underline en hover.

#### Sección 5: Distribución de Sentimientos

Donut chart o bar chart horizontal. Positivo (`tertiary`), Neutro (`secondary`), Negativo (`error`).

---

### 2. `/upload` — Data Upload & Processing

Referencia visual: `stitch/data_upload_processing/`

#### Área de Drag & Drop

- Card grande central: `border-2 border-dashed border-primary/30 bg-surface-container rounded-card`
- Texto: "Drag guest reviews here" en `font-headline text-xl`
- Formatos aceptados: CSV, JSON, TXT
- Botón secundario "Browse Files"
- Estado activo de drag: borde `border-primary`, glow dorado sutil

#### Panel de Procesamiento Activo

Aparece tras la carga. Muestra:
- Título "Active Neural Processing" (`font-headline text-xl`)
- Barra de progreso animada con color `primary`
- Lista de insights en tiempo real ("Processing Insights")
- Indicador de estado tipo spinner o pulse

#### Historial de Uploads Recientes

Tabla o lista: nombre de archivo, fecha, cantidad de reseñas, estado (badge `.tag-ok` / `.tag-warn`), acción de ver resultados.

---

### 3. `/register` — Account Registration

Referencia visual: `stitch/account_registration/`

Layout de pantalla completa, sin sidebar ni topbar. Fondo `bg-background`. Acentos ambientales: orbs difusos de color `primary/10` y `tertiary/5` en las esquinas.

#### Contenido

- Logotipo "Hoteles OLH" centrado, `font-headline italic text-4xl text-primary`
- Subtítulo "Sentiment Intelligence Suite"
- Card de registro: `bg-surface-container-low rounded-card p-10`
- Campos de input (sin box, solo `border-b-2`): email, contraseña
- Selector de sucursal hotelera (dropdown con estilo glassmorphism)
- Checkbox de términos: estilo custom `text-primary`
- CTA "Create Account": `gradient-gold`, full width, uppercase, tracking-widest
- Link "Already have an account? Sign in"
- Efecto "Sentiment Pulse": orb circular animado (breathing, scale 5%) en color `tertiary` detrás de la card

---

### 4. `/admin` — System Administration

Referencia visual: `stitch/system_administration/`

#### Header de Página

Título "System Administration" en `font-headline text-4xl font-bold`. Subtítulo descriptivo.

#### Bento Grid de Configuración

4 secciones en grid, todas con `bg-surface-container rounded-card`, sin bordes:

1. **Sentiment Thresholds:** Sliders para umbrales de Positivo / Neutro / Negativo con etiquetas `label-sm uppercase`.
2. **Topic Taxonomy:** Lista de tópicos activos (Rooms, Service, Food, Location, Noise, Cleanliness) con toggle switches estilo custom (thumb dorado sobre track oscuro).
3. **User Governance:** Tabla de usuarios con columnas Nombre, Rol, Sucursal, Estado. Sin líneas divisorias. Separación por espacio vertical. Botón "Invite User" ghost.
4. **Data Stewardship:** Botones de acción para exportar datos, limpiar caché, ver logs. Versión del sistema en `label-sm`.

#### Footer de Acción

Barra pegada al fondo con botones "Save Changes" (`gradient-gold`) y "Reset to Defaults" (ghost).

---

## Componentes Compartidos

Crear en `components/`:

| Componente | Descripción |
|---|---|
| `SentimentChip` | Pill con variantes: positive (`tertiary-container`), critical (`error-container`), alert (`primary-container`) |
| `MetricCard` | Card con score grande, label, subtexto y variación opcional |
| `SectionDivider` | Línea decorativa con label dorado (clase `.section-divider`) |
| `GradientButton` | Botón CTA con gradient-gold |
| `GhostButton` | Botón sin fondo, texto `on-surface`, underline en hover |
| `InputField` | Input sin caja, solo border-bottom, focus color primary |
| `SentimentPulse` | Orb animado breathing (keyframe scale 0.95–1.0) |
| `TopicBar` | Barra de progreso thin para scores por tópico |

---

## Datos de Ejemplo (Mock Data)

Usar datos ficticios pero realistas mientras no hay backend:

```ts
// lib/mock-data.ts
export const sentimentScore = 72;
export const sentimentDelta = +1.42;
export const topicScores = [
  { name: "Ubicación",  score: 88, sentiment: "positive" },
  { name: "Servicio",   score: 76, sentiment: "positive" },
  { name: "Limpieza",   score: 73, sentiment: "positive" },
  { name: "Habitaciones", score: 69, sentiment: "alert" },
  { name: "Comida",     score: 64, sentiment: "alert" },
  { name: "Ruido",      score: 58, sentiment: "critical" },
];
export const recentReviews = [
  { id: 1, text: "Excelente ubicación, muy céntrico y accesible...", sentiment: "positive", date: "2025-04-08" },
  { id: 2, text: "El ruido de la calle fue un problema durante la noche...", sentiment: "critical", date: "2025-04-07" },
  // ...
];
```

---

## Notas de Implementación

- Usar siempre `font-headline` (Noto Serif) para números grandes y títulos editoriales
- Usar `font-label` (Inter) en `uppercase tracking-widest` para etiquetas y metadatos
- El modo oscuro es **permanente** (`class="dark"` en `<html>`). No implementar toggle de tema.
- Íconos: usar **Material Symbols Outlined** via CDN o web font. No usar Heroicons ni Lucide para mantener coherencia.
- No usar componentes de UI libraries externas (shadcn, MUI, etc.) salvo que se indique explícitamente.
- Todas las transiciones: `duration-300`, `ease-in-out`.
- Los gráficos pueden implementarse con **Recharts** (recomendado para Next.js) o **Chart.js**.
