# POC – Panel de Sentimiento de Reviews (Tesis)

Prueba de concepto del dashboard ejecutivo para el análisis de sentimiento de reseñas del hotel.

## Contenido

- **Comportamiento del sentimiento en el tiempo**: gráfico de línea con evolución mensual.
- **Línea de tiempo interactiva**: filtros "Últimos 3/6/12 meses" y selector de fechas Desde/Hasta.
- **Tópicos que requieren atención**: tarjetas por categoría (Ruido, Comodidad, Aseo, Amabilidad, etc.) con indicadores visuales (verde/ámbar).
- **Top 5 tópicos**: lista con acceso al detalle de cada uno (clic abre modal).
- **Tabla de rendimiento**: score, cambio % y flechas de tendencia (↑/↓) con colores UX.

## Cómo ejecutar

1. Abrir `index.html` en un navegador (doble clic o desde un servidor local).
2. Opcional: si usas extensión "Live Server" en VS Code/Cursor, clic derecho en `index.html` → "Open with Live Server".

No requiere instalación ni backend; los datos son de ejemplo en `app.js`.

## Estructura

```
Poc/
├── index.html   # Estructura del panel
├── styles.css   # Estilos (paleta azul/gris, verde/rojo/ámbar)
├── app.js       # Datos de ejemplo y lógica (Chart.js, modal, filtros)
└── README.md    # Este archivo
```

## Integración futura

- Sustituir datos estáticos por llamadas a tu API o base de datos.
- Conectar filtros de fechas al backend para filtrar por rango real.
- Ajustar tópicos y umbrales de "alerta" según el modelo de NLP de la tesis.
