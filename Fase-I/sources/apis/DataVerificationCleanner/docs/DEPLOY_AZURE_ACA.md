# Guía: Azure Container Apps para Data Verification & Cleaner

Esta guía describe cómo **preparar Azure** y **desplegar** el servicio `[DataVerificationCleanner](../)` como **Azure Container App** con **2 réplicas**, imagen en **Azure Container Registry (ACR)** y variables alineadas con `[.env.example](../.env.example)` y `[config.py](../config.py)`.

**No pegues credenciales en Git.** Usá el Portal, Azure CLI o Key Vault para valores secretos.

---

## Convenciones: Bash vs PowerShell (Windows)

Los ejemplos en **Bash** usan `export`, comillas `"$VAR"` y continuación de línea con `**\`**. En **PowerShell** (5.1 o 7.x, p. ej. *Windows PowerShell* o *PowerShell*):


| Bash                             | PowerShell                                                |
| -------------------------------- | --------------------------------------------------------- |
| `export NAME="valor"`            | `$NAME = "valor"`                                         |
| Continuar línea con `\` al final | Continuar con **acento grave** ``` al final de la línea   |
| `VAR=$(az ... -o tsv)`           | `$VAR = az ... -o tsv` (sin `$(` ni paréntesis de cierre) |
| `az ... -g "$RG_NAME"`           | `az ... -g $RG_NAME` (o `"$RG_NAME"`)                     |


**Azure CLI:** instalá la [última Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) y la extensión Container Apps (`az extension add --name containerapp`). Comprobación: `az version` y `az extension list` (versión de `containerapp`).

**Cadenas con `&` (p. ej. SAS o URL en connection string de Storage):** en PowerShell, `**&` separa comandos**. Cargá el valor entre **comillas simples** `'...'` o usá un *here-string*:

```powershell
$AZURE_CONN = @'
PEGAR_AQUI_LA_CADENA_COMPLETA_SIN_MODIFICAR
'@
az containerapp secret set -n $APP_NAME -g $RG_NAME --secrets "azure-conn=$AZURE_CONN"
```

`**curl` en Windows:** el alias `curl` de PowerShell apunta a `**Invoke-WebRequest`**. Para el binario real usá `**curl.exe**` (incluido en Windows 10+) o `Invoke-RestMethod` como en el §8.1.

---

## 1. Prerrequisitos


| Requisito                                                            | Notas                                                                                                 |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Suscripción Azure                                                    | Rol típico: **Contributor** en el grupo de recursos (o roles más finos).                              |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | Windows: instalador MSI; reiniciá la terminal tras instalar.                                          |
| Extensión Container Apps                                             | `az extension add --name containerapp` y periódicamente `az extension update --name containerapp`.    |
| **Docker Desktop** o **Podman**                                      | Build/push local hacia ACR. Con Podman, el login al ACR no usa `az acr login` sin Docker: ver §5.     |
| PostgreSQL y Storage                                                 | Ya creados o externos (Neon, Azure Database for PostgreSQL, Storage Account con contenedor de blobs). |


Iniciá sesión:

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

## 2. Checklist de recursos en Azure

Marcá a medida que crees cada ítem:

- **Grupo de recursos** (ej. `miaa-tg-olh-sentiment-analysis`; si ya existe uno, reutilizalo y usá ese nombre en `$RG_NAME` sin volver a ejecutar `az group create` salvo que quieras crear otro)
- **Región** (ej. `eastus`, `eastus2`, `brazilsouth`) — alineada con el grupo de recursos y el entorno ACA
- **Azure Container Registry** (ej. `acrolhpipeline`; nombre **globalmente único**)
- **Log Analytics workspace** (obligatorio para el entorno de Container Apps)
- **Container Apps Environment** (red y logs compartidos por las apps del entorno)
- **Container App** (esta API)
- **Reglas de red**: la app debe poder salir a **PostgreSQL** (puerto 5432 o el que uses) y a **Blob** (`https://<cuenta>.blob.core.windows.net`)

---

## 3. Variables de entorno (mapa Secret vs no secreto)


| Variable                                                    | ¿Secreto? | Descripción breve                                                         |
| ----------------------------------------------------------- | --------- | ------------------------------------------------------------------------- |
| `SECRET_KEY`                                                | Sí        | Clave Flask                                                               |
| `DB_PASSWORD`                                               | Sí        | Contraseña PostgreSQL                                                     |
| `AZURE_STORAGE_CONNECTION_STRING`                           | Sí        | Cadena de conexión del Storage Account                                    |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`                  | No        | Conexión a BD                                                             |
| `DB_SSLMODE`                                                | No        | En Neon / Azure Postgres suele ser `require`                              |
| `DB_POOL_MIN`, `DB_POOL_MAX`                                | No        | Con **2 réplicas**, conexiones máx. ≈ `2 × DB_POOL_MAX` hacia el servidor |
| `AZURE_STORAGE_CONTAINER`                                   | No        | Nombre del contenedor de blobs                                            |
| `AZURE_BLOB_PREFIX_LIMPIOS`, `AZURE_BLOB_PREFIX_PROCESADOS` | No        | Prefijos virtuales                                                        |
| `FLASK_ENV`                                                 | No        | Producción: `production`                                                  |
| `FLASK_DEBUG`                                               | No        | `false`                                                                   |
| `PORT`                                                      | No        | Debe coincidir con **target port** del ingress (por defecto **5001**)     |


---

## 4. Crear infraestructura base (ejemplo con Azure CLI)

Definí nombres una vez en la misma terminal.

**Bash**

```bash
export LOCATION="eastus2"
export RG_NAME="miaa-tg-olh-sentiment-analysis"
export ACR_NAME="acrolhpipeline"
export LAW_NAME="law-olh-pipeline"
export CAE_NAME="cae-olh-pipeline"
export APP_NAME="data-verification-cleaner"
```

**PowerShell**

```powershell
$LOCATION = "eastus2"
$RG_NAME = "miaa-tg-olh-sentiment-analysis"
$ACR_NAME = "acrolhpipeline"
$LAW_NAME = "law-olh-pipeline"
$CAE_NAME = "cae-olh-pipeline"
$APP_NAME = "data-verification-cleaner"
```

### 4.1 Grupo de recursos y ACR

Si el grupo de recursos **ya existe**, omití `az group create` o ejecutalo igual (Azure CLI suele actualizar metadatos sin error si coincide la ubicación).

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

**Bash**

```bash
az monitor log-analytics workspace create \
  --resource-group "$RG_NAME" \
  --workspace-name "$LAW_NAME"

WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group "$RG_NAME" \
  --workspace-name "$LAW_NAME" \
  --query customerId -o tsv)

WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$RG_NAME" \
  --workspace-name "$LAW_NAME" \
  --query primarySharedKey -o tsv)

az containerapp env create \
  --name "$CAE_NAME" \
  --resource-group "$RG_NAME" \
  --location "$LOCATION" \
  --logs-workspace-id "$WORKSPACE_ID" \
  --logs-workspace-key "$WORKSPACE_KEY"
```

**PowerShell** (orden completo: crear workspace → leer id y clave → crear entorno)

```powershell
az monitor log-analytics workspace create `
  --resource-group $RG_NAME `
  --workspace-name $LAW_NAME

$WORKSPACE_ID = az monitor log-analytics workspace show -g $RG_NAME --workspace-name $LAW_NAME --query customerId -o tsv
$WORKSPACE_KEY = az monitor log-analytics workspace get-shared-keys -g $RG_NAME --workspace-name $LAW_NAME --query primarySharedKey -o tsv

az containerapp env create `
  --name $CAE_NAME `
  --resource-group $RG_NAME `
  --location $LOCATION `
  --logs-workspace-id $WORKSPACE_ID `
  --logs-workspace-key $WORKSPACE_KEY
```

Si el workspace **ya existía**, no ejecutes el `workspace create`; asigná `$LAW_NAME` al nombre real y empezá por los dos `az monitor ... show` / `get-shared-keys`.

---

## 5. Construir y publicar la imagen

Contexto de rutas: desde la **raíz del monorepo Tesis** (donde está la carpeta `sources/`).

**Bash (Docker + `az acr login`)**

```bash
az acr login --name "$ACR_NAME"

IMAGE_TAG="${ACR_NAME}.azurecr.io/data-verification-cleaner:1.0.0"
docker build -t "$IMAGE_TAG" -f sources/apis/DataVerificationCleanner/Dockerfile sources/apis/DataVerificationCleanner
docker push "$IMAGE_TAG"
```

**PowerShell (Docker)**

```powershell
az acr login --name $ACR_NAME

$IMAGE_TAG = "$ACR_NAME.azurecr.io/data-verification-cleaner:1.0.0"
docker build -t $IMAGE_TAG -f sources/apis/DataVerificationCleanner/Dockerfile sources/apis/DataVerificationCleanner
docker push $IMAGE_TAG
```

**Podman (sin Docker en ejecución):** `az acr login` puede fallar con `DOCKER_COMMAND_ERROR`. Usá token y login en Podman:

```powershell
az acr login -n $ACR_NAME --expose-token
# En la salida JSON: loginServer, username (GUID de ceros), accessToken

podman login <loginServer> -u <username> -p "<accessToken>"

$IMAGE_TAG = "$ACR_NAME.azurecr.io/data-verification-cleaner:1.0.0"
podman build -t $IMAGE_TAG -f sources/apis/DataVerificationCleanner/Dockerfile sources/apis/DataVerificationCleanner
podman push $IMAGE_TAG
```

---

## 6. Crear la Container App (2 réplicas, ingress HTTPS)

### 6.1 Opción A — Usuario administrador del ACR (laboratorio)

Habilitá el admin del registro y pasá usuario/contraseña al crear la app. Rápido para pruebas; en producción usá la **opción 6.1b** (identidad + `AcrPull`).

**Bash**

```bash
az acr update -n "$ACR_NAME" --admin-enabled true
ACR_USER=$(az acr credential show -n "$ACR_NAME" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR_NAME" --query "passwords[0].value" -o tsv)

az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --environment "$CAE_NAME" \
  --image "${ACR_NAME}.azurecr.io/data-verification-cleaner:1.0.0" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --target-port 5001 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 2 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --env-vars \
    "PORT=5001" \
    "FLASK_ENV=production" \
    "FLASK_DEBUG=false"
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
  --image "$ACR_NAME.azurecr.io/data-verification-cleaner:1.0.0" `
  --registry-server "$ACR_NAME.azurecr.io" `
  --registry-username $ACR_USER `
  --registry-password $ACR_PASS `
  --target-port 5001 `
  --ingress external `
  --min-replicas 2 `
  --max-replicas 2 `
  --cpu 1.0 `
  --memory 2.0Gi `
  --env-vars "PORT=5001" "FLASK_ENV=production" "FLASK_DEBUG=false"
```

Ajustá **CPU/memoria** según pruebas reales (el pipeline usa pandas, transformers y spaCy).

### 6.1b Opción B — Identidad administrada del sistema + AcrPull (recomendado en producción)

No habilites el admin user del ACR. Flujo típico:

1. **Crear** la Container App con imagen en ACR usando un método que permita el primer pull (por ejemplo imagen pública `mcr.microsoft.com/azuredocs/containerapps-helloworld:latest` solo para crear el recurso, **o** crear con admin una vez y luego quitar credenciales del registro). La variante más limpia con solo MI:

**Bash**

```bash
az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --environment "$CAE_NAME" \
  --image "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" \
  --target-port 80 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 2 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --system-assigned

PRINCIPAL_ID=$(az containerapp show -g "$RG_NAME" -n "$APP_NAME" --query identity.principalId -o tsv)
ACR_ID=$(az acr show -n "$ACR_NAME" -g "$RG_NAME" --query id -o tsv)

az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role AcrPull \
  --scope "$ACR_ID"

az containerapp registry set \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --server "${ACR_NAME}.azurecr.io" \
  --identity system

az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --image "${ACR_NAME}.azurecr.io/data-verification-cleaner:1.0.0" \
  --target-port 5001 \
  --ingress external
```

**PowerShell**

```powershell
az containerapp create `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --environment $CAE_NAME `
  --image "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" `
  --target-port 80 `
  --ingress external `
  --min-replicas 2 `
  --max-replicas 2 `
  --cpu 1.0 `
  --memory 2.0Gi `
  --system-assigned

$PRINCIPAL_ID = az containerapp show -g $RG_NAME -n $APP_NAME --query identity.principalId -o tsv
$ACR_ID = az acr show -n $ACR_NAME -g $RG_NAME --query id -o tsv

az role assignment create --assignee $PRINCIPAL_ID --role AcrPull --scope $ACR_ID

az containerapp registry set --name $APP_NAME --resource-group $RG_NAME --server "$ACR_NAME.azurecr.io" --identity system

az containerapp update --name $APP_NAME --resource-group $RG_NAME --image "$ACR_NAME.azurecr.io/data-verification-cleaner:1.0.0" --target-port 5001 --ingress external
```

1. Ajustá variables `PORT=5001`, `FLASK_ENV`, etc., como en la opción A.
2. Si el `create` inicial ya usó tu imagen de ACR, podés omitir la imagen pública: primero `az containerapp create ... --system-assigned` con `--image ${ACR_NAME}.azurecr.io/...` **fallará** el pull hasta tener `AcrPull`. Orden alternativo: `role assignment` sobre una identidad que ya exista (identidad asignada por usuario) o usar admin solo en el primer `create` y luego migrar a MI según [Autenticación en ACR desde Container Apps](https://learn.microsoft.com/azure/container-apps/containers#managed-identity).

### 6.2 Secretos y variables de aplicación

Definí secretos en el recurso (los valores **no** van al repositorio).

**Bash**

```bash
az containerapp secret set \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --secrets "secret-key=<VALOR_SECRET_KEY>" "db-password=<VALOR_DB_PASSWORD>" "azure-conn=<VALOR_AZURE_STORAGE_CONNECTION_STRING>"
```

**PowerShell** (para `azure-conn` con `&` en la cadena, usá variable con comillas simples o here-string; ver convenciones al inicio)

```powershell
$SECRET_KEY_PLAIN = "..."   # o leer de forma segura sin loguear
$DB_PASS_PLAIN = "..."
$AZURE_CONN = @'
... cadena completa de Storage ...
'@

az containerapp secret set -n $APP_NAME -g $RG_NAME --secrets "secret-key=$SECRET_KEY_PLAIN" "db-password=$DB_PASS_PLAIN" "azure-conn=$AZURE_CONN"
```

Si preferís no interpolar secretos en la línea de comandos, usá el Portal (**Container app → Secrets**) o Key Vault.

Actualizá variables que referencian secretos (`secretref:`):

**Bash**

```bash
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --set-env-vars \
    "SECRET_KEY=secretref:secret-key" \
    "DB_PASSWORD=secretref:db-password" \
    "AZURE_STORAGE_CONNECTION_STRING=secretref:azure-conn" \
    "DB_HOST=<tu-host>" \
    "DB_PORT=5432" \
    "DB_NAME=<tu-db>" \
    "DB_USER=<tu-usuario>" \
    "DB_SSLMODE=require" \
    "AZURE_STORAGE_CONTAINER=<contenedor>" \
    "AZURE_BLOB_PREFIX_LIMPIOS=limpios" \
    "AZURE_BLOB_PREFIX_PROCESADOS=procesados"
```

**PowerShell**

```powershell
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --set-env-vars `
    "SECRET_KEY=secretref:secret-key" `
    "DB_PASSWORD=secretref:db-password" `
    "AZURE_STORAGE_CONNECTION_STRING=secretref:azure-conn" `
    "DB_HOST=<tu-host>" `
    "DB_PORT=5432" `
    "DB_NAME=<tu-db>" `
    "DB_USER=<tu-usuario>" `
    "DB_SSLMODE=require" `
    "AZURE_STORAGE_CONTAINER=<contenedor>" `
    "AZURE_BLOB_PREFIX_LIMPIOS=limpios" `
    "AZURE_BLOB_PREFIX_PROCESADOS=procesados"
```

Los nombres `secretref:` deben coincidir con los **nombres** definidos en `--secrets` (sin el valor). Tras cambiar secretos, puede hacer falta **nueva revisión** o reinicio: `az containerapp revision restart -n $APP_NAME -g $RG_NAME` (según versión de CLI y estado de la app).

### 6.3 Probes HTTP en `/health`

Si el arranque es lento (modelos), configurá **startup** y **liveness/readiness** HTTP. Referencia: [Health probes in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/health-probes).

**Dónde van en el YAML exportado** (`az containerapp show -n $APP_NAME -g $RG_NAME -o yaml`): bajo `properties.template.containers[0]`, **al mismo nivel** que `env`, `image`, `name` y `resources`. Ejemplo de ubicación (indentación típica del export de Azure):

```yaml
    - env: ...
      image: ...
      name: data-verification-cleaner
      resources:
        cpu: 1.0
        memory: 2Gi
      probes:
      - type: Startup
        ...
      - type: Liveness
        ...
      - type: Readiness
        ...
```

Los tres ítems (`Startup`, `Liveness`, `Readiness`) deben ser **hermanos** bajo `probes:` con la **misma indentación** para cada `- type:`. Un error común es desindentar `Readiness` y que YAML “rompa” el contenedor.

Ejemplo de probes (puerto **5001**):

```yaml
probes:
  - type: Startup
    httpGet:
      path: /health
      port: 5001
    initialDelaySeconds: 30
    periodSeconds: 10
    failureThreshold: 30
    timeoutSeconds: 5
  - type: Liveness
    httpGet:
      path: /health
      port: 5001
    periodSeconds: 30
    failureThreshold: 3
    timeoutSeconds: 5
  - type: Readiness
    httpGet:
      path: /health
      port: 5001
    initialDelaySeconds: 10
    periodSeconds: 10
    failureThreshold: 3
    timeoutSeconds: 5
```

Flujo: `az containerapp show ... -o yaml > app.yaml` → editar `probes` → `az containerapp update -n $APP_NAME -g $RG_NAME --yaml app.yaml`.

**Aviso:** el YAML completo del `show` incluye propiedades de solo lectura (`id`, `systemData`, `outboundIpAddresses`, etc.). Si `update --yaml` falla, recortá el archivo a lo que acepte la API o usá la plantilla del repo: `[../deploy/aca/container-app.template.yaml](../deploy/aca/container-app.template.yaml)` (sustituí IDs y nombres antes de usar).

---

## 7. Red: PostgreSQL y Blob

Esta sección es un **checklist de conectividad**, no un bloque obligatorio de comandos.


| Destino                       | Qué verificar                                                                                                                |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Blob Storage**              | Salida HTTPS a Internet desde Container Apps suele bastar. Secreto `azure-conn` correcto y contenedor/prefijos en variables. |
| **PostgreSQL (Neon / Azure)** | Si hay **allowlist / firewall**, permití las **IPs de salida** de la app (o integración VNet si la BD es solo privada).      |


**Obtener IPs de salida (PowerShell o Bash)**

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.outboundIpAddresses" -o tsv
```

En Neon: [IP allowlist](https://neon.tech/docs/manage/projects#ip-allow). En Azure Database for PostgreSQL: reglas de firewall. Si la BD está en **VNet** sin endpoint público, el Container Apps Environment puede requerir **integración de red** (subred delegada). Documentación: [Red en Azure Container Apps](https://learn.microsoft.com/azure/container-apps/networking), [Firewall en Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/flexible-server/concepts-firewall-rules).

---

## 8. Verificación post-deploy

### 8.1 Health y URL pública

**Bash**

```bash
FQDN=$(az containerapp show -n "$APP_NAME" -g "$RG_NAME" --query "properties.configuration.ingress.fqdn" -o tsv)
curl -sS "https://${FQDN}/health"
```

**PowerShell**

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
Invoke-RestMethod -Uri "https://$FQDN/health"
# o: curl.exe -sS "https://$FQDN/health"
```

Respuesta esperada: JSON con `"ok": true` y `"service": "data-verification-cleaner"`.

### 8.2 Réplicas (2 instancias)

**Bash**

```bash
az containerapp show -n "$APP_NAME" -g "$RG_NAME" --query "properties.template.scale" -o json
```

**PowerShell**

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.scale" -o json
```

Deberías ver `"minReplicas": 2` y `"maxReplicas": 2`.

Réplicas en ejecución:

**Bash**

```bash
REV=$(az containerapp show -n "$APP_NAME" -g "$RG_NAME" --query "properties.latestRevisionName" -o tsv)
az containerapp replica list -n "$APP_NAME" -g "$RG_NAME" --revision "$REV" -o table
```

**PowerShell**

```powershell
$REV = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.latestRevisionName" -o tsv
az containerapp replica list -n $APP_NAME -g $RG_NAME --revision $REV -o table
```

En el Portal: **Container app → Replicas** (dos entradas en estado **Running** cuando la revisión está sana).

### 8.3 Logs

**Bash**

```bash
az containerapp logs show -n "$APP_NAME" -g "$RG_NAME" --follow
```

**PowerShell**

```powershell
az containerapp logs show -n $APP_NAME -g $RG_NAME --follow
```

Si el comando no está disponible, usá **Log Analytics** del workspace vinculado al entorno ACA (`Tables` → `ContainerAppConsoleLogs` / `ContainerAppSystemLogs`, según retención y versión del proveedor).

### 8.4 Prueba funcional API

`POST https://<FQDN>/api/v1/verificacion/ejecutar` con body JSON según el [README del servicio](../README.md), usando un blob de prueba en `AZURE_STORAGE_CONTAINER`. Confirmá en BD (`log_archivos`) y en Blob que el flujo completó sin error.

**Ejemplo Bash**

```bash
FQDN=$(az containerapp show -n "$APP_NAME" -g "$RG_NAME" --query "properties.configuration.ingress.fqdn" -o tsv)
curl -sS -X POST "https://${FQDN}/api/v1/verificacion/ejecutar" \
  -H "Content-Type: application/json" \
  -d '{"hotel_id":1,"drive_id_origen":"entrada/ejemplo.csv","nombre_archivo_origen":"ejemplo.csv","plataforma":"booking"}'
```

**Ejemplo PowerShell** (evita escapar JSON manualmente)

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
$body = @{
  hotel_id = 1
  drive_id_origen = "entrada/ejemplo.csv"
  nombre_archivo_origen = "ejemplo.csv"
  plataforma = "booking"
} | ConvertTo-Json
curl.exe -sS -X POST "https://$FQDN/api/v1/verificacion/ejecutar" -H "Content-Type: application/json" -d $body
```

---

## 8.5 Verificación local de la imagen (Docker o Podman)

Desde la raíz del monorepo Tesis.

**Docker**

```bash
docker build -t data-verification-cleaner:local -f sources/apis/DataVerificationCleanner/Dockerfile sources/apis/DataVerificationCleanner
docker run --rm -p 5001:5001 -e PORT=5001 data-verification-cleaner:local
```

**PowerShell (Docker)**

```powershell
docker build -t data-verification-cleaner:local -f sources/apis/DataVerificationCleanner/Dockerfile sources/apis/DataVerificationCleanner
docker run --rm -p 5001:5001 -e PORT=5001 data-verification-cleaner:local
```

**Podman:** mismas órdenes sustituyendo `docker` por `podman`.

En otra terminal: `curl.exe http://localhost:5001/health` o `Invoke-RestMethod http://localhost:5001/health`. Para probar persistencia y Blob necesitás el resto de variables (`-e` / `--env-file`, etc.).

---

## 9. Actualizar versión de imagen

**Bash**

```bash
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RG_NAME" \
  --image "${ACR_NAME}.azurecr.io/data-verification-cleaner:1.0.1"
```

**PowerShell**

```powershell
az containerapp update --name $APP_NAME --resource-group $RG_NAME --image "$ACR_NAME.azurecr.io/data-verification-cleaner:1.0.1"
```

---

## 10. Archivos relacionados en el repo


| Archivo                                                                               | Uso                                                              |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `[Dockerfile](../Dockerfile)`                                                         | Imagen de producción (Gunicorn + spaCy + caché del tokenizador). |
| `[wsgi.py](../wsgi.py)`                                                               | Entrada WSGI para Gunicorn.                                      |
| `[deploy/aca/container-app.template.yaml](../deploy/aca/container-app.template.yaml)` | Esqueleto YAML para `az containerapp create/update --yaml`.      |


Para CI/CD, automatizá build → push ACR → `az containerapp update --image` (GitHub Actions, Azure DevOps, etc.).