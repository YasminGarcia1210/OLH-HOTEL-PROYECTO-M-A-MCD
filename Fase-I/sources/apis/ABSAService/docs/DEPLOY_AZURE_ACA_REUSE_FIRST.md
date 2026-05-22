# Guía: despliegue en Azure Container Apps reutilizando recursos (ABSA Service)

Esta guía aplica a `[ABSAService](../)` como **Azure Container App**, priorizando **reutilizar recursos ya existentes**. Regla: antes de crear un recurso, comprobar si ya existe.

- Artefacto: `sources/apis/ABSAService`
- Imagen recomendada: `absa-service`
- Puerto: `5003` (alineado con `[.env.example](../.env.example)` y `[config.py](../config.py)`)
- Health: `GET /health` → JSON con `"service": "absa-service"`

**No commitees credenciales.** Usá secretos de la Container App, Key Vault o el Portal.

## 1) Prerrequisitos

- Azure CLI: `az login` y `az account set --subscription "<SUBSCRIPTION_ID>"`
- Extensión Container Apps:

```powershell
az extension add --name containerapp
az extension update --name containerapp
```

- Docker (o Podman) para build/push hacia ACR.

## 2) Variables base (PowerShell)

Definí una vez al inicio de la sesión:

```powershell
$LOCATION = "eastus2"
$RG_NAME = "miaa-tg-olh-sentiment-analysis"
$ACR_NAME = "acrolhpipeline"
$LAW_NAME = "law-olh-pipeline"
$CAE_NAME = "cae-olh-pipeline"
$APP_NAME = "absa-service"
$IMAGE_TAG = "$ACR_NAME.azurecr.io/absa-service:1.0.0"
```

Ajustá nombres a los recursos reales de tu suscripción.

## 3) Verificar existencia (reuse-first)

Si el comando devuelve datos, el recurso **existe** → no lo vuelvas a crear.

```powershell
az group exists --name $RG_NAME
az acr show --name $ACR_NAME --resource-group $RG_NAME --query "name" -o tsv
az monitor log-analytics workspace show --resource-group $RG_NAME --workspace-name $LAW_NAME --query "name" -o tsv
az containerapp env show --name $CAE_NAME --resource-group $RG_NAME --query "name" -o tsv
az containerapp show --name $APP_NAME --resource-group $RG_NAME --query "name" -o tsv
```

### Matriz rápida


| Recurso        | Si existe                             | Si no existe                                      |
| -------------- | ------------------------------------- | ------------------------------------------------- |
| Resource group | Reutilizar `$RG_NAME`                 | `az group create`                                 |
| ACR            | Reutilizar; build/push a ese registro | `az acr create`                                   |
| Log Analytics  | Reutilizar; leer id/clave para CAE    | `az monitor log-analytics workspace create`       |
| Entorno ACA    | Reutilizar `$CAE_NAME`                | `az containerapp env create` (necesita workspace) |
| Container App  | `az containerapp update`              | `az containerapp create`                          |


## 4) Crear solo lo faltante (PowerShell)

`az` no lanza excepciones de PowerShell por defecto; usá `$LASTEXITCODE` tras cada comprobación.

### 4.1 Resource group

```powershell
if ((az group exists --name $RG_NAME) -eq "false") {
  az group create --name $RG_NAME --location $LOCATION
}
```

### 4.2 ACR

```powershell
az acr show --name $ACR_NAME --resource-group $RG_NAME 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  az acr create --resource-group $RG_NAME --name $ACR_NAME --sku Basic
}
```

### 4.3 Log Analytics

```powershell
az monitor log-analytics workspace show --resource-group $RG_NAME --workspace-name $LAW_NAME 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  az monitor log-analytics workspace create --resource-group $RG_NAME --workspace-name $LAW_NAME --location $LOCATION
}
```

### 4.4 Container Apps Environment

```powershell
$WORKSPACE_ID = az monitor log-analytics workspace show --resource-group $RG_NAME --workspace-name $LAW_NAME --query customerId -o tsv
$WORKSPACE_KEY = az monitor log-analytics workspace get-shared-keys --resource-group $RG_NAME --workspace-name $LAW_NAME --query primarySharedKey -o tsv

az containerapp env show --name $CAE_NAME --resource-group $RG_NAME 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  az containerapp env create `
    --name $CAE_NAME `
    --resource-group $RG_NAME `
    --location $LOCATION `
    --logs-workspace-id $WORKSPACE_ID `
    --logs-workspace-key $WORKSPACE_KEY
}
```

## 5) Build y push de la imagen

Desde la **raíz del repositorio** (donde está la carpeta `sources/`):

```powershell
az acr login --name $ACR_NAME
docker build -t $IMAGE_TAG -f sources/apis/ABSAService/Dockerfile sources/apis/ABSAService
docker push $IMAGE_TAG
```

### 5.1 Con Podman

Sin Docker en ejecución, `az acr login` puede fallar con `DOCKER_COMMAND_ERROR`. Obtené un token y autenticá Podman contra el ACR:

```powershell
az acr login -n $ACR_NAME --expose-token
```

En la salida JSON usá `loginServer`, `username` (suele ser un GUID) y `accessToken`:

```powershell
podman login <loginServer> -u <username> -p "<accessToken>"

podman build -t $IMAGE_TAG -f sources/apis/ABSAService/Dockerfile sources/apis/ABSAService
podman push $IMAGE_TAG
```

Sustituí `<loginServer>` y `<username>` por los valores devueltos por Azure CLI; el token caduca: repetí login si el push falla por no autorizado.

Versionado: cambiá el tag (`1.0.1`, etc.) en `$IMAGE_TAG` antes de cada release (igual con Docker o Podman).

## 6) Desplegar la Container App

### Camino A: la app no existe (`create`)

Ejemplo con usuario administrador del ACR (rápido en laboratorio). En producción preferí identidad administrada + rol `AcrPull` (ver guías generales de ACA).

```powershell
az acr update -n $ACR_NAME --admin-enabled true
$ACR_USER = az acr credential show -n $ACR_NAME --query username -o tsv
$ACR_PASS = az acr credential show -n $ACR_NAME --query "passwords[0].value" -o tsv

az containerapp create `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --environment $CAE_NAME `
  --image $IMAGE_TAG `
  --registry-server "$ACR_NAME.azurecr.io" `
  --registry-username $ACR_USER `
  --registry-password $ACR_PASS `
  --target-port 5003 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 2 `
  --cpu 2.0 `
  --memory 4.0Gi `
  --env-vars "PORT=5003" "FLASK_ENV=production" "FLASK_DEBUG=false"
```

CPU/memoria: el backend **deberta** y modelos Hugging Face son exigentes; ajustá tras pruebas reales.

### Camino B: la app ya existe (`update`)

```powershell
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --image $IMAGE_TAG `
  --set-env-vars "PORT=5003" "FLASK_ENV=production" "FLASK_DEBUG=false"
```

## 7) Secretos y variables de aplicación

### Mapa (referencia `[.env.example](../.env.example)`)


| Variable / secreto                                                                       | Notas                                                    |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `SECRET_KEY`                                                                             | Secreto                                                  |
| `DATABASE_URL`                                                                           | Secreto (URL completa con usuario/contraseña)            |
| `OPENAI_API_KEY`                                                                         | Secreto si `LLM_PROVIDER=openai`                         |
| `GEMINI_API_KEY`                                                                         | Secreto si `LLM_PROVIDER=gemini`                         |
| Resto (`ABSA_MODEL_BACKEND`, `LLM_PROVIDER`, `DB_POOL_*`, modelos, URLs de Ollama, etc.) | Suele ser no sensible; igual podés centralizarlos en ACA |


Con **2 réplicas**, conexiones a PostgreSQL ≈ `2 × DB_POOL_MAX` (véase `DB_POOL_MAX` en `.env.example`).

### Definir secretos en la app

```powershell
$SECRET_KEY_PLAIN = "..."   # cargar de forma segura
$DATABASE_URL = @'
postgresql://usuario:password@host:5432/nombre_bd
'@

az containerapp secret set -n $APP_NAME -g $RG_NAME --secrets "secret-key=$SECRET_KEY_PLAIN" "database-url=$DATABASE_URL"
```

Si usás OpenAI o Gemini, añadí claves en el mismo `secret set` (p. ej. `openai-api-key=...`, `gemini-api-key=...`).

### Referenciar secretos y variables no sensibles

Ejemplo mínimo (LLM vía OpenAI); adaptá `LLM_PROVIDER` y claves según tu entorno:

```powershell
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --set-env-vars `
    "SECRET_KEY=secretref:secret-key" `
    "DATABASE_URL=secretref:database-url" `
    "DB_POOL_MIN=1" `
    "DB_POOL_MAX=10" `
    "ABSA_MODEL_BACKEND=llm" `
    "LLM_PROVIDER=openai" `
    "OPENAI_API_KEY=secretref:openai-api-key" `
    "OPENAI_MODEL=gpt-4o-mini" `
    "OPENAI_BATCH_POLL_ENABLED=false" `
    "OPENAI_BATCH_POLL_INTERVAL_SEC=120"
```

Para `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL` debe ser **alcanzable desde la red saliente de Container Apps** (URL pública, túnel controlado o red integrada); `localhost` no sirve dentro del contenedor salvo que Ollama vaya en el mismo pod (no es el caso por defecto).

Cadenas con `&` en URLs: en PowerShell usá comillas simples o *here-string* (`@' ... '@`) al pasar valores a `az`.

## 8) Verificación post-deploy

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
Invoke-RestMethod -Uri "https://$FQDN/health"
```

Esperado: `"ok": true` y `"service": "absa-service"`.

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.scale" -o json
az containerapp logs show -n $APP_NAME -g $RG_NAME --follow
```

## 9) Despliegue declarativo (YAML opcional)

Plantilla con placeholders: `[../deploy/aca/container-app.reuse-first.template.yaml](../deploy/aca/container-app.reuse-first.template.yaml)`. Completá marcadores y aplicá `create` o `update --yaml` según exista o no la app (detalle en `[../deploy/aca/README_REUSE_FIRST.md](../deploy/aca/README_REUSE_FIRST.md)`).

## 10) Checklist reuse-first

- Comprobaste RG, ACR, LAW, CAE y app antes de crear duplicados.
- Solo ejecutaste `create` para recursos que faltaban.
- Si la app existía, usaste `update` para imagen/config.
- Secretos solo en ACA (no en Git).
- Imagen con tag versionado.

## 11) Archivos relacionados en el repo


| Archivo                                                                                                       | Uso                                        |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `[Dockerfile](../Dockerfile)`                                                                                 | Imagen producción (Gunicorn, PyTorch CPU). |
| `[wsgi.py](../wsgi.py)`                                                                                       | Entrada WSGI.                              |
| `[deploy/aca/container-app.reuse-first.template.yaml](../deploy/aca/container-app.reuse-first.template.yaml)` | Plantilla ACA.                             |
| `[deploy/aca/README_REUSE_FIRST.md](../deploy/aca/README_REUSE_FIRST.md)`                                     | Uso rápido de la plantilla.                |


