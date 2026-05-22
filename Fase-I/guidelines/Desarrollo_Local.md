# Desarrollo local: API del dashboard y aplicación Next.js

Instrucciones para levantar en tu máquina el **DashboardBackend** (Flask) y el front **olh-sentiment-ia** (Next.js), que consumen métricas y el explorador de reseñas.

---

## Requisitos previos

- **Python 3** (entorno virtual recomendado) y, si usas el proyecto con **uv**, tener [uv](https://docs.astral.sh/uv/) instalado.
- **Node.js** y **npm** (o el gestor que prefieras) para el front.
- **PostgreSQL** accesible (por ejemplo Neon), con el esquema y datos alineados con `guidelines/ddl_bd.sql` y los servicios que alimentan métricas.

---

## 1. Backend — DashboardBackend

**Ruta:** `sources/apis/DashboardBackend/`

### Pasos

1. Abrir una terminal y situarse en esa carpeta.
2. Copiar el ejemplo de entorno y editarlo:
   ```bash
   cp .env.example .env
   ```
3. Completar en `.env` las variables de base de datos (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE`, etc.) según tu instancia.
4. Instalar dependencias (elige una opción):
   ```bash
   uv sync
   ```
   o:
   ```bash
   pip install -r requirements.txt
   ```
5. Arrancar el servidor:
   ```bash
   python app.py
   ```

### Puerto y comprobación

- Por defecto el servicio escucha en el puerto **5002** (`PORT` en `.env`).
- Comprobar estado: `GET http://127.0.0.1:5002/health`

### Tests (opcional)

```bash
uv run --group dev pytest
```

---

## 2. Frontend — olh-sentiment-ia

**Ruta:** `sources/app/olh-sentiment-ia/`

### Pasos

1. Abrir otra terminal y situarse en esa carpeta.
2. Instalar dependencias:
   ```bash
   npm install
   ```
3. Arrancar en modo desarrollo:
   ```bash
   npm run dev
   ```
4. Abrir en el navegador: **http://localhost:3000**

### Variables de entorno del front

El cliente HTTP usa por defecto `http://127.0.0.1:5002`. Si el backend corre en otro host o puerto, crea `.env.local` en la raíz del proyecto Next con:

| Variable | Descripción |
|----------|-------------|
| `NEXT_PUBLIC_DASHBOARD_API_URL` | URL base del DashboardBackend (ej. `http://127.0.0.1:5002`) |
| `NEXT_PUBLIC_DASHBOARD_HOTEL_ID` | ID de hotel por defecto (por defecto `1`) |

Tras cambiar `.env.local`, reinicia `npm run dev`.

---

## Orden recomendado

1. Levantar **DashboardBackend** (puerto **5002** si quieres coincidir con el valor por defecto del front).
2. Levantar **Next.js** con `npm run dev`.
3. Verificar que la base de datos tenga datos; sin filas en las tablas que lee la API, algunas pantallas pueden verse vacías o con mensajes de error.

---

## Otros servicios del monorepo

Existen APIs adicionales bajo `sources/apis/` (por ejemplo **SentimentPrediction**, **DataVerificationCleanner**, **MetricProcessor**). Cada una tiene su propio `README.md` y `.env.example`. El front del dashboard enlazado arriba consume principalmente **DashboardBackend**.

---

*Documento alineado con `sources/apis/DashboardBackend/README.md` y la configuración del cliente en `sources/app/olh-sentiment-ia/lib/reviews-api.ts`.*
