# Guía: despliegue en Azure Container Apps reutilizando recursos (MetricProcessor)

Esta guía aplica a `[MetricProcessor](../)` como **Azure Container App**, priorizando **reutilizar recursos ya existentes**. Regla: antes de crear un recurso, comprobar si ya existe.

- Artefacto: `sources/apis/MetricProcessor`
- Imagen recomendada: `metric-processor`
- Puerto: `5004` (alineado con `[.env.example](../.env.example)` y `[config.py](../config.py)`)
- Health: `GET /health` → JSON con `"service": "metric-processor"`

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
$APP_NAME = "metric-processor"
$IMAGE_TAG = "$ACR_NAME.azurecr.io/metric-processor:1.0.0"
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
docker build -t $IMAGE_TAG -f sources/apis/MetricProcessor/Dockerfile sources/apis/MetricProcessor
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

podman build -t $IMAGE_TAG -f sources/apis/MetricProcessor/Dockerfile sources/apis/MetricProcessor
podman push $IMAGE_TAG
```

Sustituí `<loginServer>` y `<username>` por los valores devueltos por Azure CLI; el token caduca: repetí login si el push falla por no autorizado.

Versionado: cambiá el tag (`1.0.1`, etc.) en `$IMAGE_TAG` antes de cada release (igual con Docker o Podman).

## 6) Desplegar la Container App

### Camino A: la app no existe (`create`)

Ejemplo con usuario administrador del ACR (rápido en laboratorio). En producción preferí identidad administrada + rol `AcrPull` (documentación de Microsoft sobre ACA y ACR).

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
  --target-port 5004 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 2 `
  --cpu 1.0 `
  --memory 2.0Gi `
  --env-vars "PORT=5004" "FLASK_ENV=production" "FLASK_DEBUG=false"
```

### Camino B: la app ya existe (`update`)

```powershell
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --image $IMAGE_TAG `
  --set-env-vars "PORT=5004" "FLASK_ENV=production" "FLASK_DEBUG=false"
```

## 7) Secretos y variables de aplicación

### Mapa (referencia `[.env.example](../.env.example)`)


| Variable                                                 | Notas                                                                              |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `SECRET_KEY`                                             | Secreto                                                                            |
| `DB_PASSWORD`                                            | Secreto                                                                            |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_SSLMODE` | No secretos en muchos entornos                                                     |
| `DB_POOL_MIN`, `DB_POOL_MAX`                             | No; con **2 réplicas** las conexiones máximas hacia PostgreSQL ≈ `2 × DB_POOL_MAX` |


### Definir secretos en la app

```powershell
$SECRET_KEY_PLAIN = "..."
$DB_PASS_PLAIN = "..."

az containerapp secret set -n $APP_NAME -g $RG_NAME --secrets "secret-key=$SECRET_KEY_PLAIN" "db-password=$DB_PASS_PLAIN"
```

### Referenciar secretos y variables de conexión

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
    "DB_POOL_MAX=10"
```

Si la contraseña u otros valores tienen caracteres especiales para PowerShell, usá *here-string* (`@' ... '@`) al asignar variables antes de `secret set`.

## 8) Red (PostgreSQL)

La app debe poder alcanzar PostgreSQL (puerto típico `5432`). Si tu proveedor usa **allowlist / firewall**, permití las **IPs de salida** de la Container App:

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.outboundIpAddresses" -o tsv
```

## 9) Verificación post-deploy

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
Invoke-RestMethod -Uri "https://$FQDN/health"
```

Esperado: `"ok": true` y `"service": "metric-processor"`.

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.scale" -o json
az containerapp logs show -n $APP_NAME -g $RG_NAME --follow
```

Prueba funcional opcional: `POST https://$FQDN/api/v1/metricas/calcular` con body `{"archivo_id": <id>}` según el [README del servicio](../README.md).

## 10) Despliegue declarativo (YAML opcional)

Plantilla con placeholders: `[../deploy/aca/container-app.reuse-first.template.yaml](../deploy/aca/container-app.reuse-first.template.yaml)`. Completá marcadores y aplicá `create` o `update --yaml` según exista o no la app (detalle en `[../deploy/aca/README_REUSE_FIRST.md](../deploy/aca/README_REUSE_FIRST.md)`).

## 11) Checklist reuse-first

- Comprobaste RG, ACR, LAW, CAE y app antes de crear duplicados.
- Solo ejecutaste `create` para recursos que faltaban.
- Si la app existía, usaste `update` para imagen/config.
- Secretos solo en ACA (no en Git).
- Imagen con tag versionado.

## 12) Archivos relacionados en el repo


| Archivo                                                                                                       | Uso                           |
| ------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| `[Dockerfile](../Dockerfile)`                                                                                 | Imagen producción (Gunicorn). |
| `[wsgi.py](../wsgi.py)`                                                                                       | Entrada WSGI.                 |
| `[deploy/aca/container-app.reuse-first.template.yaml](../deploy/aca/container-app.reuse-first.template.yaml)` | Plantilla ACA.                |
| `[deploy/aca/README_REUSE_FIRST.md](../deploy/aca/README_REUSE_FIRST.md)`                                     | Uso rápido de la plantilla.   |


