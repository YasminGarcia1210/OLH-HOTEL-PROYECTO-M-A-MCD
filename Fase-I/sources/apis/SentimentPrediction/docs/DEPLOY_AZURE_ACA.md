# Guía: Azure Container Apps para Sentiment Prediction

Esta guía describe cómo **desplegar** el servicio `[SentimentPrediction](../)` como **Azure Container App** con **2 réplicas**, imagen en **Azure Container Registry (ACR)** y variables alineadas con `[.env.example](../.env.example)` y `[config.py](../config.py)`.

Si ya desplegaste **Data Verification Cleaner** en el mismo proyecto, podés **reutilizar** grupo de recursos, ACR, Log Analytics y el entorno de Container Apps; sólo sumás una **nueva imagen** y una **nueva Container App**. El detalle está en el [§2](#2-reutilizar-recursos-de-dataverificationcleanner).

**No pegues credenciales en Git.** Usá el Portal, Azure CLI o Key Vault para valores secretos.

---

## Convenciones: Bash vs PowerShell (Windows)

Los ejemplos en **Bash** usan `export`, comillas `"$VAR"` y continuación de línea con `**\`**. En **PowerShell** (5.1 o 7.x):


| Bash                             | PowerShell                                              |
| -------------------------------- | ------------------------------------------------------- |
| `export NAME="valor"`            | `$NAME = "valor"`                                       |
| Continuar línea con `\` al final | Continuar con **acento grave** ``` al final de la línea |
| `VAR=$(az ... -o tsv)`           | `$VAR = az ... -o tsv`                                  |


**Azure CLI:** instalá la [última Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) y la extensión Container Apps (`az extension add --name containerapp`).

**Región (`$LOCATION`):** En la CLI se usa el **id** de ubicación, no el nombre del portal. *East US* → `eastus`; **East US 2** → `**eastus2`**. Son regiones distintas: si tu infra está en East US 2, sustituí `eastus` por `**eastus2`** en todos los ejemplos y mantené la misma región en el grupo de recursos, el ACR y el entorno de Container Apps. Para listar ids: `az account list-locations --query "[].name" -o tsv`.

Para cadenas con `&` u otros caracteres especiales en PowerShell, usá comillas simples o *here-string* (igual que en la guía del otro API: `[DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md)`).

`**curl` en Windows:** usá `**curl.exe`** o `Invoke-RestMethod` (ver §8.1).

---

## 1. Prerrequisitos


| Requisito                                                                                       | Notas                                                                                              |
| ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Suscripción Azure                                                                               | Rol típico: **Contributor** en el grupo de recursos.                                               |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) + extensión `containerapp` | `az extension add --name containerapp`                                                             |
| **Docker** o **Podman**                                                                         | Build y push hacia ACR (véase la guía del Cleaner para Podman y `az acr login`).                   |
| PostgreSQL                                                                                      | Mismo servidor que el pipeline u otro; la app necesita acceso **TCP 5432** (o el puerto que uses). |


**Bash**

```bash
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

**PowerShell**

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

---

## 2. Reutilizar recursos de DataVerificationCleanner

Si completaste `[../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md)`, estos recursos **no hace falta volver a crearlos** para Sentiment Prediction:


| Recurso Azure                                | Reutilización  | Notas                                                                                                                                |
| -------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Grupo de recursos** (`$RG_NAME`)           | Sí             | Usá el mismo nombre (p. ej. `miaa-tg-olh-sentiment-analysis`).                                                                       |
| **Azure Container Registry** (`$ACR_NAME`)   | Sí             | Publicá una imagen adicional: `sentiment-prediction:<tag>` en el mismo ACR.                                                          |
| **Log Analytics workspace** (`$LAW_NAME`)    | Sí             | Ya vinculado al entorno ACA existente.                                                                                               |
| **Container Apps Environment** (`$CAE_NAME`) | Sí             | Desplegá esta API como **otra** Container App en el mismo entorno.                                                                   |
| **Container App**                            | No             | Es un **nuevo** recurso (p. ej. `sentiment-prediction`), independiente de `data-verification-cleaner`.                               |
| **PostgreSQL**                               | Normalmente sí | Mismo host/usuario que el resto del pipeline; `DB_NAME` suele alinearse con el esquema (por defecto `olh_sentiment` en `config.py`). |
| **Storage / Blob**                           | No aplica      | Este servicio **no** usa `AZURE_STORAGE_CONNECTION_STRING`.                                                                          |


**Flujo resumido si ya tenés infra:** definí `$RG_NAME`, `$ACR_NAME`, `$CAE_NAME` como en el despliegue anterior → [§5](#5-construir-y-publicar-la-imagen) (build/push) → [§6](#6-crear-la-container-app-2-réplicas-ingress-https) con `$APP_NAME="sentiment-prediction"` y **puerto 5003** → [§6.2](#62-secretos-y-variables-de-aplicación) (secretos y env) → verificación.

### 2.1 Checklist (solo lo nuevo para esta API)

- **Imagen** en ACR: `sentiment-prediction:1.0.0` (o el tag que elijas)
- **Container App** `sentiment-prediction` en el entorno `$CAE_NAME` existente
- **Variables** de BD y modelo (sin Blob)
- **Red**: salida a PostgreSQL (firewall / allowlist si aplica)

Si **no** tenés aún RG, ACR, workspace ni entorno ACA, seguí el [§4](#4-crear-infraestructura-base-ejemplo-con-azure-cli) (misma secuencia que en la guía del Cleaner; podés usar los mismos nombres de recursos compartidos).

---

## 3. Variables de entorno (mapa Secret vs no secreto)


| Variable                                   | ¿Secreto? | Descripción breve                                                                                                 |
| ------------------------------------------ | --------- | ----------------------------------------------------------------------------------------------------------------- |
| `SECRET_KEY`                               | Sí        | Clave Flask                                                                                                       |
| `DB_PASSWORD`                              | Sí        | Contraseña PostgreSQL                                                                                             |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | No        | Conexión a BD                                                                                                     |
| `DB_SSLMODE`                               | No        | En Neon / Azure Postgres suele ser `require`                                                                      |
| `DB_POOL_MIN`, `DB_POOL_MAX`               | No        | Con **2 réplicas**, conexiones máx. ≈ `2 × DB_POOL_MAX`                                                           |
| `SENTIMENT_MODEL_DIR`                      | No        | En la imagen Docker: ruta **dentro del contenedor**, p. ej. `/app/models/p91` (el modelo va copiado en la imagen) |
| `SENTIMENT_MODEL_VERSION`                  | No        | Ej. `p91` (etiqueta de versión lógica)                                                                            |
| `SENTIMENT_BATCH_SIZE`                     | No        | Tamaño de lote para inferencia                                                                                    |
| `SENTIMENT_DEVICE`                         | No        | En ACA sin GPU: `cpu`                                                                                             |
| `SENTIMENT_MAX_INPUT_CHARS`                | No        | Opcional; límite de caracteres en `/predecir`                                                                     |
| `FLASK_ENV`                                | No        | Producción: `production`                                                                                          |
| `FLASK_DEBUG`                              | No        | `false`                                                                                                           |
| `PORT`                                     | No        | Debe coincidir con **target port** del ingress: **5003** (valor por defecto en `config.py`)                       |


---

## 4. Crear infraestructura base (ejemplo con Azure CLI)

**Omití esta sección completa** si ya creaste RG, ACR, Log Analytics y el entorno ACA al desplegar Data Verification Cleaner.

**Bash**

```bash
export LOCATION="eastus2"
export RG_NAME="miaa-tg-olh-sentiment-analysis"
export ACR_NAME="acrolhpipeline"
export LAW_NAME="law-olh-pipeline"
export CAE_NAME="cae-olh-pipeline"
export APP_NAME="sentiment-prediction"
```

**PowerShell**

```powershell
$LOCATION = "eastus2"
$RG_NAME = "miaa-tg-olh-sentiment-analysis"
$ACR_NAME = "acrolhpipeline"
$LAW_NAME = "law-olh-pipeline"
$CAE_NAME = "cae-olh-pipeline"
$APP_NAME = "sentiment-prediction"
```

### 4.1 Grupo de recursos y ACR

**Bash**

```bash
az group create --name "$RG_NAME" --location "$LOCATION"
az acr create --resource-group "$RG_NAME" --name "$ACR_NAME" --sku Basic
```

**PowerShell**

```powershell
az group create --name $RG_NAME --location $LOCATION
az acr create --resource-group $RG_NAME --name $ACR_NAME --sku Basic
```

### 4.2 Log Analytics y entorno de Container Apps

Copiá los comandos de la guía del Cleaner ([§4.2](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md#42-log-analytics-y-entorno-de-container-apps)): `az monitor log-analytics workspace create`, lectura de `customerId` / `primarySharedKey`, y `az containerapp env create` con esos valores.

---

## 5. Construir y publicar la imagen

Contexto de rutas: desde la **raíz del monorepo Tesis** (donde está la carpeta `sources/`).

La imagen incluye el checkpoint bajo `models/p91/` (no hace falta montar Blob para el modelo si usás esa ruta por defecto).

**Bash**

```bash
az acr login --name "$ACR_NAME"

IMAGE_TAG="${ACR_NAME}.azurecr.io/sentiment-prediction:1.0.0"
docker build -t "$IMAGE_TAG" -f sources/apis/SentimentPrediction/Dockerfile sources/apis/SentimentPrediction
docker push "$IMAGE_TAG"
```

**PowerShell**

```powershell
az acr login --name $ACR_NAME

$IMAGE_TAG = "$ACR_NAME.azurecr.io/sentiment-prediction:1.0.0"
docker build -t $IMAGE_TAG -f sources/apis/SentimentPrediction/Dockerfile sources/apis/SentimentPrediction
docker push $IMAGE_TAG
```

Para **Podman** o problemas con `az acr login`, seguí el apartado equivalente en la guía del Cleaner ([§5](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md#5-construir-y-publicar-la-imagen)).

---

## 6. Crear la Container App (2 réplicas, ingress HTTPS)

**Puerto de la aplicación:** **5003** (coherente con `config.py` y `.env.example`).

Recomendación inicial de recursos: **CPU 1.0**, **memoria 4.0Gi** (PyTorch + transformers + modelo; ajustá tras pruebas de carga).

### 6.1 Opción A — Usuario administrador del ACR (laboratorio)

**Bash**

```bash
az acr update -n "$ACR_NAME" --admin-enabled true
ACR_USER=$(az acr credential show -n "$ACR_NAME" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR_NAME" --query "passwords[0].value" -o tsv)

az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --environment "$CAE_NAME" \
  --image "${ACR_NAME}.azurecr.io/sentiment-prediction:1.0.0" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --target-port 5003 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 2 \
  --cpu 1.0 \
  --memory 4.0Gi \
  --env-vars \
    "PORT=5003" \
    "FLASK_ENV=production" \
    "FLASK_DEBUG=false" \
    "SENTIMENT_MODEL_DIR=/app/models/p91" \
    "SENTIMENT_DEVICE=cpu"
```

**PowerShell**

```powershell
az acr update -n $ACR_NAME --admin-enabled true
$ACR_USER = az acr credential show -n $ACR_NAME --query username -o tsv
$ACR_PASS = az acr credential show -n $ACR_NAME --query "passwords[0].value" -o tsv

az containerapp create `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --environment $CAE_NAME `
  --image "$ACR_NAME.azurecr.io/sentiment-prediction:1.0.0" `
  --registry-server "$ACR_NAME.azurecr.io" `
  --registry-username $ACR_USER `
  --registry-password $ACR_PASS `
  --target-port 5003 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 2 `
  --cpu 1.0 `
  --memory 4.0Gi `
  --env-vars "PORT=5003" "FLASK_ENV=production" "FLASK_DEBUG=false" "SENTIMENT_MODEL_DIR=/app/models/p91" "SENTIMENT_DEVICE=cpu"
```

### 6.1b Opción B — Identidad administrada + AcrPull

Mismo patrón que en [DataVerificationCleanner §6.1b](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md#61b-opción-b--identidad-administrada-del-sistema--acrpull-recomendado-en-producción): sustituí la imagen final por `"${ACR_NAME}.azurecr.io/sentiment-prediction:1.0.0"` y `--target-port 5003`.

### 6.2 Secretos y variables de aplicación

Este API **no** necesita secreto de Azure Storage.

**Bash**

```bash
az containerapp secret set \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --secrets "secret-key=<VALOR_SECRET_KEY>" "db-password=<VALOR_DB_PASSWORD>"
```

**PowerShell**

```powershell
az containerapp secret set -n $APP_NAME -g $RG_NAME --secrets "secret-key=$SECRET_KEY_PLAIN" "db-password=$DB_PASS_PLAIN"
```

**Bash** — variables (incluyendo `secretref:`)

```bash
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --set-env-vars \
    "SECRET_KEY=secretref:secret-key" \
    "DB_PASSWORD=secretref:db-password" \
    "DB_HOST=<tu-host>" \
    "DB_PORT=5432" \
    "DB_NAME=<tu-db>" \
    "DB_USER=<tu-usuario>" \
    "DB_SSLMODE=require" \
    "DB_POOL_MIN=1" \
    "DB_POOL_MAX=10" \
    "SENTIMENT_MODEL_DIR=/app/models/p91" \
    "SENTIMENT_MODEL_VERSION=p91" \
    "SENTIMENT_BATCH_SIZE=8" \
    "SENTIMENT_DEVICE=cpu"
```

**PowerShell**

```powershell
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --set-env-vars `
    "SECRET_KEY=secretref:secret-key" `
    "DB_PASSWORD=secretref:db-password" `
    "DB_HOST=<tu-host>" `
    "DB_PORT=5432" `
    "DB_NAME=<tu-db>" `
    "DB_USER=<tu-usuario>" `
    "DB_SSLMODE=require" `
    "DB_POOL_MIN=1" `
    "DB_POOL_MAX=10" `
    "SENTIMENT_MODEL_DIR=/app/models/p91" `
    "SENTIMENT_MODEL_VERSION=p91" `
    "SENTIMENT_BATCH_SIZE=8" `
    "SENTIMENT_DEVICE=cpu"
```

### 6.3 Probes HTTP en `/health`

El arranque puede ser **lento** (carga del modelo en CPU). Configurá **startup** con margen (p. ej. `initialDelaySeconds` alto y `failureThreshold` amplio). Referencia: [Health probes in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/health-probes).

Ejemplo (puerto **5003**); ubicación en el YAML exportado: bajo `properties.template.containers[0].probes` (misma estructura que documenta el Cleaner):

```yaml
probes:
  - type: Startup
    httpGet:
      path: /health
      port: 5003
    initialDelaySeconds: 60
    periodSeconds: 15
    failureThreshold: 40
    timeoutSeconds: 10
  - type: Liveness
    httpGet:
      path: /health
      port: 5003
    periodSeconds: 30
    failureThreshold: 3
    timeoutSeconds: 10
  - type: Readiness
    httpGet:
      path: /health
      port: 5003
    initialDelaySeconds: 20
    periodSeconds: 10
    failureThreshold: 3
    timeoutSeconds: 10
```

Plantilla en el repo: `[../deploy/aca/container-app.template.yaml](../deploy/aca/container-app.template.yaml)`.

---

## 7. Red: PostgreSQL


| Destino        | Qué verificar                                                                                                      |
| -------------- | ------------------------------------------------------------------------------------------------------------------ |
| **PostgreSQL** | Allowlist / firewall: permití las **IPs de salida** de la Container App (mismo procedimiento que para el Cleaner). |


**IPs de salida**

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.outboundIpAddresses" -o tsv
```

---

## 8. Verificación post-deploy

### 8.1 Health y URL pública

**PowerShell**

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
Invoke-RestMethod -Uri "https://$FQDN/health"
```

Respuesta esperada: JSON con `"ok": true` y `"service": "sentiment-prediction"`.

### 8.2 Réplicas

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.scale" -o json
$REV = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.latestRevisionName" -o tsv
az containerapp replica list -n $APP_NAME -g $RG_NAME --revision $REV -o table
```

### 8.3 Logs

```powershell
az containerapp logs show -n $APP_NAME -g $RG_NAME --follow
```

### 8.4 Prueba funcional API (predicción síncrona)

**PowerShell**

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
$body = @{ texto = "Excelente estadía, volvería sin dudar." } | ConvertTo-Json
curl.exe -sS -X POST "https://$FQDN/api/v1/sentimiento/predecir" -H "Content-Type: application/json" -d $body
```

Para flujos asíncronos por archivo (`POST /api/v1/sentimiento/procesar`), necesitás datos coherentes en la BD (mismo pipeline que el Cleaner).

---

## 8.5 Verificación local de la imagen

Desde la raíz del monorepo Tesis.

**PowerShell**

```powershell
docker build -t sentiment-prediction:local -f sources/apis/SentimentPrediction/Dockerfile sources/apis/SentimentPrediction
docker run --rm -p 5003:5003 -e PORT=5003 sentiment-prediction:local
```

En otra terminal: `Invoke-RestMethod http://localhost:5003/health`. Para probar contra PostgreSQL real, pasá `-e` / `--env-file` con las variables de BD.

---

## 9. Actualizar versión de imagen

**PowerShell**

```powershell
az containerapp update --name $APP_NAME --resource-group $RG_NAME --image "$ACR_NAME.azurecr.io/sentiment-prediction:1.0.1"
```

---

## 10. Archivos relacionados en el repo


| Archivo                                                                               | Uso                                                                 |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `[Dockerfile](../Dockerfile)`                                                         | Imagen de producción (Gunicorn + PyTorch CPU + modelo empaquetado). |
| `[wsgi.py](../wsgi.py)`                                                               | Entrada WSGI para Gunicorn.                                         |
| `[deploy/aca/container-app.template.yaml](../deploy/aca/container-app.template.yaml)` | Esqueleto YAML para `az containerapp create/update --yaml`.         |


Para CI/CD: build → push ACR → `az containerapp update --image` (mismo patrón que el otro API en el mismo ACR).

---

## Referencia cruzada

- Infra compartida y convenciones detalladas (PowerShell, SAS, Podman): `[../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md)`

