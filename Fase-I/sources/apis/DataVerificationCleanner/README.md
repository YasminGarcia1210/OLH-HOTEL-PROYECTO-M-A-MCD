# Data Verification & Cleaner Service

Servicio REST responsable de validar, limpiar y persistir las reseñas hoteleras.
Es el **primer componente del pipeline de NLP** de la Fase 1.

---

## Despliegue en Azure (Container Apps)

- Guía paso a paso: [`docs/DEPLOY_AZURE_ACA.md`](docs/DEPLOY_AZURE_ACA.md)
- Plantilla YAML y punteros: [`deploy/aca/README.md`](deploy/aca/README.md)
- Contenedor: [`Dockerfile`](Dockerfile), WSGI: [`wsgi.py`](wsgi.py)

---

## Responsabilidades

| # | Paso | Detalle |
|---|------|---------|
| 1 | Descargar CSV | Descarga el archivo de reviews desde **Azure Blob Storage** (ruta dentro del contenedor configurado) |
| 2 | Validar estructura | Verifica columnas requeridas (`review`, `fecha`) y formato ISO en fechas |
| 3 | Ejecutar pipeline de limpieza | Limpieza de texto (encoding, HTML, emojis, ruido, longitud) con detección de idioma |
| 4 | Persistir en BD | INSERT atómico en `log_archivos` + `reviews` (PostgreSQL / Neon) |
| 5 | Subir CSV limpio | Sube el CSV limpio al prefijo configurado en Azure *(configurable, desactivado por defecto)* |
| 6 | Mover archivo original | Copia el blob origen al prefijo **procesados** y lo borra en la ruta original *(configurable, desactivado por defecto)* |

---

## Estructura del proyecto

```
DataVerificationCleanner/
├── app.py                        # Entry point y factory de Flask
├── wsgi.py                       # Entrada WSGI (Gunicorn en contenedor)
├── Dockerfile                  # Imagen de producción
├── config.py                     # Configuración desde variables de entorno
├── db.py                         # Pool de conexiones PostgreSQL (psycopg2)
├── requirements.txt              # Dependencias Python
├── .env.example                  # Plantilla de variables de entorno
│
├── docs/
│   └── DEPLOY_AZURE_ACA.md       # Guía: preparar Azure y desplegar en ACA
├── deploy/aca/                   # Plantilla YAML Container Apps
│
├── config/
│   └── pipeline.yaml             # Parámetros del pipeline y flags de operaciones
│
├── lib/
│   └── cleaning_pipeline.py      # Pipeline de limpieza de texto (librería interna)
│
├── routes/
│   ├── __init__.py
│   ├── verificacion.py           # Blueprint con los endpoints del servicio
│   └── validators.py             # Validaciones del body de cada endpoint
│
├── services/
│   ├── cleaning_service.py       # Orquesta la ejecución del pipeline de limpieza
│   ├── csv_validator_service.py  # Valida estructura y contenido del CSV
│   ├── azure_blob_service.py     # Descarga, sube y mueve blobs en Azure Storage
│   └── exceptions.py            # Excepciones de dominio del servicio
│
└── repositories/
    ├── log_archivos_repository.py # Acceso a la tabla log_archivos
    └── reviews_repository.py      # Acceso a la tabla reviews (insert bulk)
```

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/health` | Health check del servicio |
| `POST` | `/api/v1/verificacion/ejecutar` | Inicia el proceso completo de verificación y limpieza |
| `GET`  | `/api/v1/verificacion/archivos/<id>` | Consulta el estado de un archivo procesado |
| `GET`  | `/api/v1/verificacion/archivos` | Lista archivos filtrados por hotel y/o estado |

### POST /ejecutar — Body

El campo `drive_id_origen` conserva el nombre histórico del contrato; su valor es la **ruta del blob** dentro del contenedor `AZURE_STORAGE_CONTAINER` (por ejemplo `entrada/reviews_hotel_nov2025.csv`).

```json
{
  "hotel_id": 1,
  "drive_id_origen": "entrada/reviews_hotel_nov2025.csv",
  "nombre_archivo_origen": "reviews_hotel_nov2025.csv",
  "plataforma": "booking"
}
```

### POST /ejecutar — Respuesta exitosa

`drive_id_limpio` es la ruta del blob generado tras la subida (vacío si la subida está desactivada o falla la configuración).

```json
{
  "ok": true,
  "data": {
    "archivo_id": 42,
    "nombre_archivo_origen": "reviews_hotel_nov2025.csv",
    "nombre_archivo_limpio": "reviews_hotel_nov2025_clean.csv",
    "drive_id_limpio": "limpios/reviews_hotel_nov2025_clean.csv",
    "estado": "cleaned",
    "total_registros": 100,
    "registros_validos": 98,
    "registros_descartados": 2
  },
  "error": null
}
```

### Códigos de error

Los códigos `*_DRIVE` se mantienen por compatibilidad con integraciones existentes; el almacenamiento real es **Azure Blob Storage**.

| Código | HTTP | Causa |
|--------|------|-------|
| `BODY_INVALIDO` | 400 | Campos requeridos faltantes o con tipo incorrecto |
| `ARCHIVO_YA_PROCESADO` | 409 | El archivo ya existe en `log_archivos` con estado distinto a `error` |
| `ARCHIVO_NO_ENCONTRADO_EN_DRIVE` | 404 | El blob de origen no existe o las credenciales no tienen acceso |
| `CREDENCIALES_DRIVE_INVALIDAS` | 503 | Cadena de conexión o contenedor Azure no configurados o inválidos |
| `ERROR_DESCARGA_DRIVE` | 502 | Error de red o del servicio durante la descarga |
| `ESTRUCTURA_INVALIDA` | 422 | Columnas faltantes o fechas con formato no ISO |
| `CSV_SIN_DATOS` | 422 | CSV vacío o más del 50% de reviews vacías |
| `PIPELINE_SIN_RESULTADOS` | 422 | El pipeline eliminó todas las filas |
| `ERROR_PIPELINE_LIMPIEZA` | 500 | Error interno durante la limpieza de texto |
| `ERROR_PERSISTENCIA` | 500 | Fallo al insertar en la base de datos |
| `ERROR_SUBIDA_DRIVE` | 502 | Fallo al subir el CSV limpio (p. ej. blob destino ya existente) |
| `ERROR_MOVER_DRIVE` | 502 | Fallo al mover el archivo original |

---

## Instalación y ejecución

```bash
# 1. Crear entorno virtual
py -m venv .venv

# 2. Activar entorno (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelo spaCy (solo primera vez)
python -m spacy download es_core_news_sm

# 5. Configurar variables de entorno
copy .env.example .env
# Editar .env con los valores reales (Azure Storage, base de datos, etc.)

# 6. Ejecutar el servicio
python app.py
```

El servicio queda disponible en `http://localhost:5001`.

> **Nota:** La primera ejecución del pipeline descarga el tokenizador BERT
> `dccuchile/bert-base-spanish-wwm-cased` desde HuggingFace. Requiere internet.

---

## Configuración del pipeline (`config/pipeline.yaml`)

El archivo controla el comportamiento del pipeline sin modificar código.

### Sección `operaciones`

```yaml
operaciones:
  subir_csv_limpio: false        # true → sube CSV limpio al prefijo AZURE_BLOB_PREFIX_LIMPIOS
  mover_archivo_original: false  # true → mueve el blob origen a AZURE_BLOB_PREFIX_PROCESADOS
```

### Perfiles de limpieza

| Parámetro | `prediccion` | `entrenamiento` | Descripción |
|-----------|:---:|:---:|-------------|
| `deduplicar` | `false` | `true` | Elimina reviews duplicadas |
| `filtrar_idioma` | `false` | `true` | Elimina reviews en otro idioma |
| `min_palabras` | `3` | `5` | Mínimo de palabras por review |
| `min_tokens` | `4` | `6` | Mínimo de tokens BERT por review |
| `max_tokens` | `512` | `512` | Máximo antes de truncar |
| `umbral_confianza_idioma` | `0.75` | `0.75` | Confianza mínima del detector |
| `modo` | `bert` | `bert` | `bert` conserva tildes/ñ |

---

## Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Entorno de ejecución | `development` |
| `FLASK_DEBUG` | Modo debug | `true` |
| `PORT` | Puerto del servicio | `5001` |
| `SECRET_KEY` | Clave secreta Flask | — |
| `DB_HOST` | Host PostgreSQL | `localhost` |
| `DB_PORT` | Puerto PostgreSQL | `5432` |
| `DB_NAME` | Nombre de la base de datos | `olh_sentiment` |
| `DB_USER` | Usuario PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña PostgreSQL | — |
| `DB_SSLMODE` | Modo SSL (requerido en Neon) | `require` |
| `DB_POOL_MIN` | Conexiones mínimas en el pool | `1` |
| `DB_POOL_MAX` | Conexiones máximas en el pool | `10` |
| `AZURE_STORAGE_CONNECTION_STRING` | Cadena de conexión del Storage Account | — |
| `AZURE_STORAGE_CONTAINER` | Nombre del contenedor de blobs | — |
| `AZURE_BLOB_PREFIX_LIMPIOS` | Prefijo virtual para CSV limpios (p. ej. `limpios`) | — |
| `AZURE_BLOB_PREFIX_PROCESADOS` | Prefijo virtual para archivos ya procesados | — |

---

## Dependencias principales

| Librería | Uso |
|----------|-----|
| `flask` + `flask-cors` | Framework REST |
| `psycopg2-binary` | Conexión PostgreSQL con pool de conexiones |
| `pandas` | Procesamiento del DataFrame |
| `azure-storage-blob` | Cliente de Azure Blob Storage |
| `transformers` | Tokenizador BERT para control de longitud |
| `spacy` + `es_core_news_sm` | Anonimización de nombres propios |
| `lingua-language-detector` | Detección de idioma por review |
| `rapidfuzz` | Deduplicación fuzzy (modo entrenamiento) |
| `beautifulsoup4` | Limpieza de HTML en reviews |
| `pyyaml` | Lectura del archivo de configuración |
