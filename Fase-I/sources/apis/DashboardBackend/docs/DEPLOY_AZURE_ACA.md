# Guía: Azure Container Apps para Dashboard Backend

Esta guía describe cómo **desplegar** el servicio `[DashboardBackend](../)` como **Azure Container App** con **mínimo 0** y **máximo 5 réplicas**, imagen en **Azure Container Registry (ACR)**, variables alineadas con `[.env.example](../.env.example)` y `[config.py](../config.py)`, y arranque con **Gunicorn** (`[wsgi.py](../wsgi.py)`).

Si ya desplegaste otra API del mismo proyecto (p. ej. Data Verification Cleaner), podés **reutilizar** grupo de recursos, ACR, Log Analytics y el entorno de Container Apps; sumás una **nueva imagen** y una **nueva Container App**. Resumen de comprobaciones “reuse-first”: [ABSAService/docs/DEPLOY_AZURE_ACA_REUSE_FIRST.md](../../ABSAService/docs/DEPLOY_AZURE_ACA_REUSE_FIRST.md).

**No pegues credenciales en Git.** Usá el Portal, Azure CLI o Key Vault para valores secretos.

---

## Convenciones: Bash vs PowerShell (Windows)

| Bash                             | PowerShell                                              |
| -------------------------------- | ------------------------------------------------------- |
| `export NAME="valor"`            | `$NAME = "valor"`                                       |
| Continuar línea con `\` al final | Continuar con **acento grave** (backtick) al final de la línea |
| `VAR=$(az ... -o tsv)`           | `$VAR = az ... -o tsv`                                  |

**Azure CLI:** [instalación](https://learn.microsoft.com/cli/azure/install-azure-cli) y extensión Container Apps:

```powershell
az extension add --name containerapp
az extension update --name containerapp
```

**Región (`$LOCATION`):** usá el **id** de ubicación (`eastus2`, no “East US 2” del portal). Si tu infra está en **East US 2**, usá `eastus2` de forma consistente en RG, ACR y entorno ACA.

**Cadenas con `&` (p. ej. connection string de Storage):** en PowerShell, `&` separa comandos. Usá **comillas simples** o *here-string*:

```powershell
$AZURE_CONN = @'
PEGAR_AQUI_LA_CADENA_COMPLETA
'@
az containerapp secret set -n $APP_NAME -g $RG_NAME --secrets "azure-conn=$AZURE_CONN"
```

**`curl` en Windows:** el alias apunta a `Invoke-WebRequest`. Para HTTP clásico usá **`curl.exe`** o `Invoke-RestMethod`.

---

## 1. Prerrequisitos

| Requisito | Notas |
| --------- | ----- |
| Suscripción Azure | Rol típico: **Contributor** en el grupo de recursos. |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | Reiniciá la terminal tras instalar en Windows. |
| Extensión Container Apps | Comandos arriba. |
| **Podman** o Docker | Build/push hacia ACR. Con Podman, si `az acr login` falla sin Docker, usá token (§5). |
| PostgreSQL y Storage | Neon, Azure Database for PostgreSQL, Storage Account con contenedor de blobs (mismos que usa el dashboard en `.env`). |

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

---

## 2. Checklist de recursos en Azure

- **Grupo de recursos** (ej. `miaa-tg-olh-sentiment-analysis`)
- **Región** alineada con RG, ACR y entorno ACA
- **Azure Container Registry** (nombre globalmente único)
- **Log Analytics workspace** (obligatorio para el entorno ACA)
- **Container Apps Environment**
- **Container App** (esta API)
- **Red de salida:** HTTPS a Blob; PostgreSQL en el puerto configurado (`DB_PORT`, típicamente 5432)

---

## 3. Variables de entorno (mapa secreto vs no secreto)

| Variable | ¿Secreto? | Descripción breve |
| -------- | --------- | ------------------- |
| `SECRET_KEY` | Sí | Clave Flask |
| `JWT_SECRET_KEY` | Sí (recomendado) | Firma JWT; si no se define, en código cae en `SECRET_KEY` ([config.py](../config.py)) |
| `DB_PASSWORD` | Sí | Contraseña PostgreSQL |
| `AZURE_STORAGE_CONNECTION_STRING` | Sí | Cadena de conexión del Storage Account |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | No | Conexión a BD |
| `DB_SSLMODE` | No | En Neon / Azure Postgres suele ser `require` |
| `DB_POOL_MIN`, `DB_POOL_MAX` | No | Con **hasta 5 réplicas**, conexiones máx. aprox. `5 × DB_POOL_MAX`; ajustá según límites del proveedor |
| `AZURE_STORAGE_CONTAINER` | No | Nombre del contenedor de blobs |
| `AZURE_BLOB_PREFIX_UPLOAD`, `AZURE_BLOB_LIST_EXCLUDE_PREFIXES` | No | Prefijos y exclusiones de listado (ver `.env.example`) |
| `FLASK_ENV` | No | Producción: `production` |
| `FLASK_DEBUG` | No | `false` |
| `PORT` | No | Debe coincidir con **target port** del ingress (**5002**) |
| `UPLOAD_MAX_BYTES` | No | Opcional; por defecto 50 MiB en código |
| `JWT_ALGORITHM` | No | Algoritmo de firma JWT; default `HS256` ([config.py](../config.py)) |
| `JWT_ACCESS_TOKEN_MINUTES` | No | Vida del access token en minutos; default `30` |
| `JWT_REFRESH_TOKEN_DAYS` | No | Vida del refresh token en días; default `30` |
| `METRIC_PROCESSOR_URL` | No | URL base del servicio MetricProcessor para `POST /api/v1/metricas/recalcular-semestre`. En ACA típicamente `https://metric-processor.<env-domain>` |
| `METRIC_PROCESSOR_TIMEOUT_SECONDS` | No | Timeout HTTP por cada mes recalculado (default `30`; el recálculo semestral hace hasta 6 llamadas, ⇒ peor caso `6 × timeout`) |

---

## 4. Variables base (PowerShell)

Definí al inicio de la sesión (ajustá a tus recursos reales):

```powershell
$LOCATION = "eastus2"
$RG_NAME = "miaa-tg-olh-sentiment-analysis"
$ACR_NAME = "acrolhpipeline"
$LAW_NAME = "law-olh-pipeline"
$CAE_NAME = "cae-olh-pipeline"
$APP_NAME = "dashboard-backend"
$IMAGE_TAG = "$ACR_NAME.azurecr.io/dashboard-backend:1.0.0"
```

### 4.1 Reutilizar recursos (no recrear si ya existen)

```powershell
az group exists --name $RG_NAME
az acr show --name $ACR_NAME --resource-group $RG_NAME --query "name" -o tsv
az monitor log-analytics workspace show --resource-group $RG_NAME --workspace-name $LAW_NAME --query "name" -o tsv
az containerapp env show --name $CAE_NAME --resource-group $RG_NAME --query "name" -o tsv
```

Si falta alguno, seguí la guía completa de otro servicio para crear RG, ACR, workspace y entorno: [DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md) (§4).

---

## 5. Construir y publicar la imagen

**Importante:** el `[Dockerfile](../Dockerfile)` copia `libs/metricas_read` y `apis/DashboardBackend`. El **contexto de build** debe ser la carpeta **`sources/`** (relativa a la raíz del repo `Tesis`, donde existe `sources/libs` y `sources/apis`).

Desde la **raíz del monorepo** `Tesis`:

**PowerShell (Docker + `az acr login`)**

```powershell
az acr login --name $ACR_NAME

$IMAGE_TAG = "$ACR_NAME.azurecr.io/dashboard-backend:1.0.0"
docker build `
  --ignorefile sources/apis/DashboardBackend/context.dockerignore `
  -t $IMAGE_TAG -f sources/apis/DashboardBackend/Dockerfile sources
docker push $IMAGE_TAG
```

**Podman (sin Docker en ejecución):** si `az acr login` devuelve `DOCKER_COMMAND_ERROR`, usá token:

```powershell
az acr login -n $ACR_NAME --expose-token
# En la salida: loginServer, username (GUID), accessToken

podman login <loginServer> -u <username> -p "<accessToken>"

$IMAGE_TAG = "$ACR_NAME.azurecr.io/dashboard-backend:1.0.0"
podman build `
  --ignorefile sources/apis/DashboardBackend/context.dockerignore `
  -t $IMAGE_TAG -f sources/apis/DashboardBackend/Dockerfile sources
podman push $IMAGE_TAG
```

Si usás **Podman Machine** en Windows, asegurate de que esté iniciada: `podman machine start`.

### 5.1 El `podman build` parece colgado (sin salida)

- **Contexto enorme (muy frecuente):** con `sources` como contexto, sin filtrar se incluyen **otras APIs**, `app/`, `data/`, modelos (`SentimentPrediction/models`, etc.). Podman empaqueta todo y lo sube a la VM **sin imprimir nada** → parece colgado. **Solución:** usá siempre `--ignorefile sources/apis/DashboardBackend/context.dockerignore` (archivo en el repo).
- **Frontend Dockerfile (`# syntax=docker/dockerfile:1`)**: en Podman puede implicar pull de `docker.io/docker/dockerfile` y quedar mucho tiempo sin mensajes. El `Dockerfile` de este servicio **no** usa esa directiva para evitarlo.
- **Primera vez**: el pull de `python:3.12-slim-bookworm` puede tardar varios minutos; no hay barra de progreso por defecto.
- **Comprobar la VM**: `podman machine list`, `podman system connection list`; si la máquina está parada, `podman machine start`.
- **Más trazas**: `podman build --log-level=debug ...` (mismos `-f`, `--ignorefile`, `-t` y `sources`; ver en qué paso se detiene). Si en debug ves `BuildLocal failed: Not Found` antes de `POST .../libpod/build`, en Podman para Windows es **normal**: intenta build local, no está disponible y delega en la VM (WSL); no es el fallo del Dockerfile.
- **Probar pull aparte**: `podman pull python:3.12-slim-bookworm` (si esto cuelga, el problema es red/registry, no el Dockerfile).

---

## 6. Crear la Container App (0–5 réplicas, ingress HTTPS, puerto 5002)

### 6.1 Opción A — Usuario administrador del ACR (laboratorio)

```powershell
az acr update -n $ACR_NAME --admin-enabled true
$ACR_USER = az acr credential show -n $ACR_NAME --query username -o tsv
$ACR_PASS = az acr credential show -n $ACR_NAME --query "passwords[0].value" -o tsv

az containerapp create `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --environment $CAE_NAME `
  --image "$ACR_NAME.azurecr.io/dashboard-backend:1.0.0" `
  --registry-server "$ACR_NAME.azurecr.io" `
  --registry-username $ACR_USER `
  --registry-password $ACR_PASS `
  --target-port 5002 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 5 `
  --cpu 0.5 `
  --memory 1.0Gi `
  --env-vars "PORT=5002" "FLASK_ENV=production" "FLASK_DEBUG=false"
```

Ajustá **CPU/memoria** según carga (subidas grandes pueden requerir más memoria).

### 6.1b Opción B — Identidad administrada + AcrPull (recomendado en producción)

Mismo flujo que en [DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md) §6.1b: crear app con imagen pública inicial o admin solo para el primer pull, asignar `AcrPull` al `principalId` de la app, `az containerapp registry set ... --identity system`, luego `az containerapp update` con la imagen del ACR y `--target-port 5002`.

---

## 6.2 Secretos y variables de aplicación

```powershell
$SECRET_KEY_PLAIN = "..."   # cargar de forma segura
$JWT_SECRET_PLAIN = "..."
$DB_PASS_PLAIN = "..."
$AZURE_CONN = @'
... connection string completa ...
'@

az containerapp secret set -n $APP_NAME -g $RG_NAME `
  --secrets "secret-key=$SECRET_KEY_PLAIN" "jwt-secret=$JWT_SECRET_PLAIN" "db-password=$DB_PASS_PLAIN" "azure-conn=$AZURE_CONN"
```

Variables que referencian secretos:

```powershell
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --set-env-vars `
    "SECRET_KEY=secretref:secret-key" `
    "JWT_SECRET_KEY=secretref:jwt-secret" `
    "DB_PASSWORD=secretref:db-password" `
    "AZURE_STORAGE_CONNECTION_STRING=secretref:azure-conn" `
    "DB_HOST=<tu-host>" `
    "DB_PORT=5432" `
    "DB_NAME=olh_sentiment" `
    "DB_USER=<tu-usuario>" `
    "DB_SSLMODE=require" `
    "DB_POOL_MIN=1" `
    "DB_POOL_MAX=10" `
    "AZURE_STORAGE_CONTAINER=<contenedor>" `
    "AZURE_BLOB_PREFIX_UPLOAD=" `
    "AZURE_BLOB_LIST_EXCLUDE_PREFIXES=limpios" `
    "UPLOAD_MAX_BYTES=52428800" `
    "JWT_ALGORITHM=HS256" `
    "JWT_ACCESS_TOKEN_MINUTES=30" `
    "JWT_REFRESH_TOKEN_DAYS=30" `
    "METRIC_PROCESSOR_URL=https://metric-processor.<env-domain>" `
    "METRIC_PROCESSOR_TIMEOUT_SECONDS=60" `
    "PORT=5002" `
    "FLASK_ENV=production" `
    "FLASK_DEBUG=false"
```

Si todavía no agregaste algunas, agregalas según [`.env.example`](../.env.example) (ver también §9.4 para el flujo de actualización incremental).

Tras cambiar secretos, si hace falta: `az containerapp revision restart -n $APP_NAME -g $RG_NAME`.

---

## 6.3 Probes HTTP en `/health`

Configurá **startup**, **liveness** y **readiness** en `GET /health` puerto **5002**. Con **minReplicas 0**, el primer arranque tras escalar desde cero puede tardar; los valores siguientes son un punto de partida (ajustá según latencia a tu BD).

Referencia: [Health probes in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/health-probes).

Ubicación en el YAML exportado: `properties.template.containers[0].probes` (hermanos de `env`).

Ejemplo:

```yaml
probes:
  - type: Startup
    httpGet:
      path: /health
      port: 5002
    initialDelaySeconds: 20
    periodSeconds: 10
    failureThreshold: 30
    timeoutSeconds: 5
  - type: Liveness
    httpGet:
      path: /health
      port: 5002
    periodSeconds: 30
    failureThreshold: 3
    timeoutSeconds: 5
  - type: Readiness
    httpGet:
      path: /health
      port: 5002
    initialDelaySeconds: 5
    periodSeconds: 10
    failureThreshold: 3
    timeoutSeconds: 5
```

Flujo típico: `az containerapp show -n $APP_NAME -g $RG_NAME -o yaml > app.yaml` → editar `probes` → `az containerapp update -n $APP_NAME -g $RG_NAME --yaml app.yaml`. Si el YAML completo falla por campos de solo lectura, usá la plantilla del repo: [`../deploy/aca/container-app.template.yaml`](../deploy/aca/container-app.template.yaml).

---

## 7. Red: PostgreSQL y Blob

| Destino | Verificación |
| ------- | ------------ |
| Blob Storage | Salida HTTPS; `azure-conn` y `AZURE_STORAGE_CONTAINER` correctos. |
| PostgreSQL | Firewall / allowlist: las **IPs de salida** de Container Apps pueden cambiar; con Neon u oros proveedores, revisá [política de IP](https://neon.tech/docs/manage/projects#ip-allow) o integración VNet si la BD es solo privada. |

**IPs de salida (PowerShell):**

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.outboundIpAddresses" -o tsv
```

---

## 8. Verificación post-deploy

### 8.1 Health y URL pública

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
Invoke-RestMethod -Uri "https://$FQDN/health"
# o: curl.exe -sS "https://$FQDN/health"
```

Respuesta esperada: JSON con `"ok": true`, `"service": "dashboard-backend"` (o el valor de `SERVICE_NAME` si lo sobrescribís).

### 8.2 Escala (0–5)

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.scale" -o json
```

Deberías ver `"minReplicas": 0` y `"maxReplicas": 5`. Con tráfico nulo, las réplicas pueden bajar a **cero** (cold start en la siguiente petición).

### 8.3 Logs

```powershell
az containerapp logs show -n $APP_NAME -g $RG_NAME --follow
```

### 8.4 Prueba funcional

Probar login (`/api/v1/...` según [README](../README.md)) y un endpoint de métricas con token. Asegurate de que migraciones SQL (`migrations/`) estén aplicadas en la base compartida.

---

## 8.5 Verificación local de la imagen (Docker o Podman)

Desde la raíz del repo `Tesis`:

```powershell
podman build `
  --ignorefile sources/apis/DashboardBackend/context.dockerignore `
  -t dashboard-backend:local -f sources/apis/DashboardBackend/Dockerfile sources
podman run --rm -p 5002:5002 -e PORT=5002 dashboard-backend:local
```

Con variables mínimas (o `--env-file`), en otra terminal: `curl.exe http://localhost:5002/health`.

---

## 9. Actualizar imagen **y** variables de entorno

### 9.1 Solo cambiar la imagen (cuando la app **ya** tiene env y secretos en ACA)

Si ya configuraste secretos y `set-env-vars` en un despliegue anterior, basta con:

```powershell
az containerapp update --name $APP_NAME --resource-group $RG_NAME --image "$ACR_NAME.azurecr.io/dashboard-backend:1.0.1"
```

Eso **no borra** las variables que ya están en la plantilla del contenedor; solo crea una revisión nueva con otra imagen.

### 9.2 Primera vez o te faltan env: secretos + `update` con imagen y variables

**Orden:** primero los secretos del recurso (§6.2), luego un solo `az containerapp update` con **`--image`** y **`--set-env-vars`** (los valores `secretref:` deben coincidir con los nombres de `--secrets`).

Ejemplo (sustituí hosts, usuario y nombres de contenedor Blob; los secretos cargalos de forma segura, no en historial):

```powershell
# 1) Secretos en el recurso (una vez o cuando roten)
az containerapp secret set -n $APP_NAME -g $RG_NAME `
  --secrets "secret-key=..." "jwt-secret=..." "db-password=..." "azure-conn=..."

# 2) Imagen nueva + todas las variables que necesita [config.py](../config.py) / [.env.example](../.env.example)
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --image "$ACR_NAME.azurecr.io/dashboard-backend:1.0.1" `
  --set-env-vars `
    "PORT=5002" `
    "FLASK_ENV=production" `
    "FLASK_DEBUG=false" `
    "SECRET_KEY=secretref:secret-key" `
    "JWT_SECRET_KEY=secretref:jwt-secret" `
    "JWT_ALGORITHM=HS256" `
    "JWT_ACCESS_TOKEN_MINUTES=30" `
    "JWT_REFRESH_TOKEN_DAYS=30" `
    "DB_PASSWORD=secretref:db-password" `
    "AZURE_STORAGE_CONNECTION_STRING=secretref:azure-conn" `
    "DB_HOST=<tu-host-neon-o-postgres>" `
    "DB_PORT=5432" `
    "DB_NAME=olh_sentiment" `
    "DB_USER=<tu-usuario>" `
    "DB_SSLMODE=require" `
    "DB_POOL_MIN=1" `
    "DB_POOL_MAX=10" `
    "AZURE_STORAGE_CONTAINER=<contenedor-blobs>" `
    "AZURE_BLOB_PREFIX_UPLOAD=" `
    "AZURE_BLOB_LIST_EXCLUDE_PREFIXES=limpios" `
    "UPLOAD_MAX_BYTES=52428800" `
    "METRIC_PROCESSOR_URL=https://metric-processor.<env-domain>" `
    "METRIC_PROCESSOR_TIMEOUT_SECONDS=60"
```

**Importante:** según versión de CLI y estado del recurso, `--set-env-vars` puede **reemplazar la lista completa** de variables del contenedor. Antes de tocar producción, listá lo que hay hoy:

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.containers[0].env" -o json
```

Copiá lo que necesites conservar y unilo con las claves nuevas en un único `--set-env-vars` (o editá YAML como en §6.3).

### 9.3 Connection string con `&` en PowerShell

Usá *here-string* para `azure-conn` (§ convenciones al inicio del documento), no pegues la cadena entre comillas dobles sueltas.

### 9.4 Agregar variables nuevas sin tocar las existentes (recomendado)

Cuando se incorpora un feature que agrega claves nuevas (p. ej. la integración con MetricProcessor en `POST /api/v1/metricas/recalcular-semestre`), `--set-env-vars` **solo agrega o actualiza** las variables listadas y conserva el resto del entorno y los `secretref`. Es la opción más segura para evitar borrar variables ya configuradas.

```powershell
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --image "$ACR_NAME.azurecr.io/dashboard-backend:1.0.1" `
  --set-env-vars `
    "DB_POOL_MIN=5" `
    "DB_POOL_MAX=200" `
    "AZURE_BLOB_PREFIX_UPLOAD=/" `
    "AZURE_BLOB_LIST_EXCLUDE_PREFIXES=limpios,procesados" `
    "UPLOAD_MAX_BYTES=52428800" `
    "JWT_ALGORITHM=HS256" `
    "JWT_ACCESS_TOKEN_MINUTES=30" `
    "JWT_REFRESH_TOKEN_DAYS=30" `
    "METRIC_PROCESSOR_URL=https://metric-processor.<env-domain>" `
    "METRIC_PROCESSOR_TIMEOUT_SECONDS=60"
```

Si la CLI cambió el comportamiento (algunas versiones reemplazaban la lista completa) o querés validarlo antes:

```powershell
# Snapshot previo
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.containers[0].env" -o json > env-before.json

# (aplicar el update)

# Snapshot posterior y diff manual
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.containers[0].env" -o json > env-after.json
```

Para quitar una variable sin tocar el resto: `--remove-env-vars NOMBRE`.

---

## 10. Archivos relacionados en el repo

| Archivo | Uso |
| ------- | --- |
| [`Dockerfile`](../Dockerfile) | Imagen (contexto `sources/`). |
| [`context.dockerignore`](../context.dockerignore) | Reducir contexto de build; pasar como `--ignorefile` (ver §5). |
| [`requirements-docker.txt`](../requirements-docker.txt) | Dependencias pip en contenedor (sin `metricas_read` editable). |
| [`wsgi.py`](../wsgi.py) | Entrada WSGI para Gunicorn. |
| [`deploy/aca/container-app.template.yaml`](../deploy/aca/container-app.template.yaml) | Plantilla YAML para `az containerapp create/update --yaml`. |

---

## Riesgos breves

- **Allowlist estricta por IP** en Neon/Postgres puede fallar con egress dinámico de ACA; preferí políticas compatibles con apps serverless o VNet.
- **Secretos en historial** de terminal: evitá pegar valores sensibles en comandos logueados; usá Portal o Key Vault cuando sea posible.

## 11. Fallo al arrancar: `ImportError: cannot import name 'Options' from 'jwt.types'`

Suele deberse a mezclar el paquete PyPI **`jwt`** con **`PyJWT`**, o a instalar **`flask-jwt-extended` 4.8+** con un stack incompatible. En este repo la imagen fija **`PyJWT==2.9.0`** y **`flask-jwt-extended==4.7.1`**, desinstala `jwt` antes del `pip install` y ejecuta **`python -c "from wsgi import app"`** en el build para detectar el fallo antes del deploy.

**Reconstruí sin caché si dudás de la capa pip**, publicá de nuevo y actualizá la Container App:

```powershell
podman build --no-cache `
  --ignorefile sources/apis/DashboardBackend/context.dockerignore `
  -t $IMAGE_TAG -f sources/apis/DashboardBackend/Dockerfile sources
```
