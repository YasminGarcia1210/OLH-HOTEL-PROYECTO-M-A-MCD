# Paleta de colores

La **fuente canónica** del sistema completo de tokens (hex y nombres) es [`cursor/instructions.md`](instructions.md) (sección *Identidad Visual: "The Nocturnal Intelligence"*). En el código los tokens viven en `app/globals.css` (`@theme inline`) y se usan como clases Tailwind (`bg-surface-container`, `text-primary`, etc.).

## Uso semántico (resumen)

| Rol | Tokens / clases típicas |
|-----|-------------------------|
| Fondo de app / base | `background`, `surface`, `surface-dim` |
| Capas y tarjetas | `surface-container-lowest` … `surface-container-highest` |
| Texto principal | `on-background`, `on-surface` (no usar blanco puro `#FFFFFF`) |
| Texto secundario / variantes | `on-surface-variant` |
| Acento / marca / KPIs destacados | `primary`, `accent`, `surface-tint`; CTAs con gradiente gold (ver `instructions.md`) |
| Positivo / éxito en datos | `tertiary`, `tertiary-container` |
| Neutro / secundario UI | `secondary`, contenedores `secondary-*` |
| Error / negativo | `error`, `error-container`, `on-error` |
| Bordes y división suave | `outline`, `outline-variant` |

Modo oscuro **fijo** (`class="dark"` en `<html>`); no alternar tema claro/oscuro salvo que el proyecto lo pida explícitamente.

# Tipografía

- **Headline / números grandes:** Noto Serif (`font-headline`)
- **Cuerpo:** Manrope (`font-body`)
- **Etiquetas y metadatos:** Inter (`font-label`), a menudo en mayúsculas con tracking amplio
- **Íconos:** Material Symbols Outlined

# Prioridades

- Trabaja pensando en reutilizar componentes y estilos.
- Crea componentes para las tarjetas o cualquier elemento que se repita
- Maneja carpetas y subcarpetas acorde a las páginas que estás trabajando
- No hagas configuraciones ni instalaciones de librerías sin consultar primero.
