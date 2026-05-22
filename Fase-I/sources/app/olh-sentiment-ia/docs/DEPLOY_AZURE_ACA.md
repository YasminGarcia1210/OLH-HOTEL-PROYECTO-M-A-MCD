# Guía: Azure Container Apps para `olh-sentiment-ia` (Frontend Next.js)

Esta guía describe cómo **desplegar** la aplicación `[olh-sentiment-ia](../)` (Next.js 16, React 19) como **Azure Container App** con **mínimo 0** y **máximo 2 réplicas**, imagen en **Azure Container Registry (ACR)** y variables alineadas con `[.env copy.example](../.env%20copy.example)`.

Si ya desplegaste otra pieza del mismo proyecto (`DashboardBackend`, `ABSAService`, etc.), podés **reutilizar** grupo de recursos, ACR, Log Analytics y el entorno de Container Apps; sólo agregás una **nueva imagen** y una **nueva Container App**. Resumen *reuse-first*: [`apis/ABSAService/docs/DEPLOY_AZURE_ACA_REUSE_FIRST.md`](../../../apis/ABSAService/docs/DEPLOY_AZURE_ACA_REUSE_FIRST.md).

> **No pegues credenciales en Git.** Usá el Portal, Azure CLI o Key Vault para valores secretos.
>
> **Importante (Next.js):** las variables `NEXT_PUBLIC_*` se inyectan en el bundle del cliente en **build time**. Cualquier cambio de URL → **rebuild + push de imagen nueva**. Ver §3 y §5.

---

## Convenciones: Bash vs PowerShell (Windows)

| Bash                             | PowerShell                                                     |
| -------------------------------- | -------------------------------------------------------------- |
| `export NAME="valor"`            | `$NAME = "valor"`                                              |
| Continuar línea con `\` al final | Continuar con **acento grave** (backtick) al final de la línea |
| `VAR=$(az ... -o tsv)`           | `$VAR = az ... -o tsv`                                         |

**Azure CLI:** [instalación](https://learn.microsoft.com/cli/azure/install-azure-cli) y extensión Container Apps:

```powershell
az extension add --name containerapp
az extension update --name containerapp
```

**Región (`$LOCATION`):** usá el **id** (`eastus2`, no “East US 2” del portal). Mantené el mismo id en RG, ACR y entorno ACA.

**`curl` en Windows:** el alias apunta a `Invoke-WebRequest`. Para HTTP clásico usá **`curl.exe`** o `Invoke-RestMethod`.

---

## 1. Prerrequisitos

| Requisito | Notas |
| --------- | ----- |
| Suscripción Azure | Rol típico: **Contributor** en el grupo de recursos. |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | Reiniciá la terminal tras instalar en Windows. |
| Extensión Container Apps | Comandos arriba. |
| **Podman** (o Docker) | Build/push hacia ACR. Con Podman, si `az acr login` falla sin Docker, usá token (§5). |
| `DashboardBackend` ya desplegado | El frontend lo necesita en `NEXT_PUBLIC_DASHBOARD_API_URL`. |
| Webhook de n8n (opcional) | Para `NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL`. |

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
- **Container App** (este frontend)
- **Red de salida:** HTTPS hacia `DashboardBackend` y hacia el webhook de n8n.

---

## 3. Variables de entorno

A diferencia de las APIs Flask, **todas** las variables de este frontend tienen el prefijo `NEXT_PUBLIC_*` y por tanto:

- Quedan **embebidas en el JS del cliente** durante `next build`.
- **No son secretos.** Tratalas como configuración pública (URL del backend, id de hotel por defecto, URL del webhook).
- Por eso van como `--build-arg` en Podman (ver §5), **no** como `secretref:` en Container Apps.

| Variable | ¿Secreto? | Descripción |
| -------- | --------- | ----------- |
| `NEXT_PUBLIC_DASHBOARD_API_URL` | No | URL pública del Dashboard Backend (sin barra final). Usado en `[lib/reviews-api.ts](../lib/reviews-api.ts)`, `[lib/upload-api.ts](../lib/upload-api.ts)`, etc. |
| `NEXT_PUBLIC_DASHBOARD_HOTEL_ID` | No | Id de hotel por defecto para `GET /api/v1/dashboard/reviews`. |
| `NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL` | No | Webhook de n8n para disparar análisis. Leído por `[components/layout/Sidebar.tsx](../components/layout/Sidebar.tsx)`. |
| `PORT` | No | Debe coincidir con el **target port** del ingress (**3000**). Lo respeta el server standalone. |
| `HOSTNAME` | No | El Dockerfile lo fija en `0.0.0.0` para que Next.js escuche fuera del contenedor. |

> Si más adelante aparecen secretos reales (claves API server-side), declaralos sin el prefijo `NEXT_PUBLIC_*` y guardalos como `secretref:` en ACA — quedarán solo en el runtime del servidor.

---

## 4. Variables base (PowerShell)

Definí al inicio de la sesión (ajustá a tus recursos reales):

```powershell
$LOCATION  = "eastus2"
$RG_NAME   = "miaa-tg-olh-sentiment-analysis"
$ACR_NAME  = "acrolhpipeline"
$LAW_NAME  = "law-olh-pipeline"
$CAE_NAME  = "cae-olh-pipeline"
$APP_NAME  = "olh-sentiment-ia"
$IMAGE_TAG = "$ACR_NAME.azurecr.io/olh-sentiment-ia:1.0.0"

# URLs públicas que se inyectarán en BUILD TIME (cambiar implica rebuild)
$DASHBOARD_API_URL  = "https://dashboard-backend.<sufijo>.eastus2.azurecontainerapps.io"
$DASHBOARD_HOTEL_ID = "1"
$ANALYSIS_WEBHOOK   = "https://n8n-olh-pipeline.<sufijo>.eastus2.azurecontainerapps.io/webhook/<id>"
```

### 4.1 Reutilizar recursos (no recrear si ya existen)

```powershell
az group exists --name $RG_NAME
az acr show --name $ACR_NAME --resource-group $RG_NAME --query "name" -o tsv
az monitor log-analytics workspace show --resource-group $RG_NAME --workspace-name $LAW_NAME --query "name" -o tsv
az containerapp env show --name $CAE_NAME --resource-group $RG_NAME --query "name" -o tsv
```

Si falta alguno, seguí la guía de otro servicio para crear RG, ACR, workspace y entorno: [`apis/DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md`](../../../apis/DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md) (§4).

---

## 5. Construir y publicar la imagen

**Importante:** el `[Dockerfile](../Dockerfile)` está pensado para que el **contexto de build** sea la propia carpeta del frontend (`sources/app/olh-sentiment-ia`), no `sources/`. No depende de `libs/` ni de `apis/`.

Las URLs públicas se pasan como **`--build-arg`** porque Next.js inyecta `NEXT_PUBLIC_*` en el JS del cliente durante `next build` (sin esto, el bundle queda con el fallback `http://127.0.0.1:5002`).

Desde la **raíz del monorepo** `Tesis`:

### 5.1 Podman (sin Docker en ejecución)

Si `az acr login` devuelve `DOCKER_COMMAND_ERROR`, usá token:

```powershell
az acr login -n $ACR_NAME --expose-token
# En la salida JSON: loginServer, username (GUID de ceros), accessToken

podman login <loginServer> -u <username> -p "<accessToken>"

podman build `
  --ignorefile sources/app/olh-sentiment-ia/context.dockerignore `
  --build-arg NEXT_PUBLIC_DASHBOARD_API_URL=$DASHBOARD_API_URL `
  --build-arg NEXT_PUBLIC_DASHBOARD_HOTEL_ID=$DASHBOARD_HOTEL_ID `
  --build-arg NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL=$ANALYSIS_WEBHOOK `
  -t $IMAGE_TAG `
  -f sources/app/olh-sentiment-ia/Dockerfile `
  sources/app/olh-sentiment-ia

podman push $IMAGE_TAG
```

Si usás **Podman Machine** en Windows, asegurate de que esté iniciada: `podman machine start`.

### 5.2 Docker (alternativa)

```powershell
az acr login --name $ACR_NAME

docker build `
  --build-arg NEXT_PUBLIC_DASHBOARD_API_URL=$DASHBOARD_API_URL `
  --build-arg NEXT_PUBLIC_DASHBOARD_HOTEL_ID=$DASHBOARD_HOTEL_ID `
  --build-arg NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL=$ANALYSIS_WEBHOOK `
  -t $IMAGE_TAG `
  -f sources/app/olh-sentiment-ia/Dockerfile `
  sources/app/olh-sentiment-ia

docker push $IMAGE_TAG
```

### 5.3 El `podman build` parece colgado (sin salida)

- **Contexto sucio (lo más frecuente):** `node_modules/` y `.next/` locales pesan cientos de MB → Podman empaqueta todo y lo sube a la VM **sin imprimir nada**. **Solución:** usá siempre `--ignorefile sources/app/olh-sentiment-ia/context.dockerignore`.
- **Pull de `node:22-alpine`** la primera vez puede tardar varios minutos sin barra de progreso.
- **`next build` con `next/font/google`** descarga las fuentes durante el build → asegurate de tener salida a Internet desde Podman Machine.
- **Más trazas:** `podman build --log-level=debug ...`. En Windows + Podman, ver `BuildLocal failed: Not Found` antes de `POST .../libpod/build` es **normal** (intenta build local, no está disponible y delega en la VM/WSL).
- **Probar pull aparte:** `podman pull node:22-alpine` (si esto cuelga, el problema es red/registry, no el Dockerfile).

---

## 6. Crear la Container App (0–2 réplicas, ingress HTTPS, puerto 3000)

### 6.1 Opción A — Usuario administrador del ACR (laboratorio)

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
  --target-port 3000 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 2 `
  --cpu 0.5 `
  --memory 1.0Gi `
  --env-vars "PORT=3000" "HOSTNAME=0.0.0.0" "NODE_ENV=production"
```

> Las `NEXT_PUBLIC_*` **no** hace falta repetirlas como `--env-vars` porque ya están dentro del bundle. Las dejamos sólo si querés que un endpoint server-side de Next.js (route handlers) las lea en runtime — no es el caso actual.

### 6.1b Opción B — Identidad administrada + AcrPull (recomendado en producción)

Mismo flujo que en [`apis/DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md`](../../../apis/DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md) §6.1b: crear app con imagen pública inicial, asignar `AcrPull` al `principalId` de la app, `az containerapp registry set ... --identity system`, luego `az containerapp update` con la imagen del ACR y `--target-port 3000`.

---

## 6.2 Probes HTTP

Con **minReplicas 0**, el primer arranque tras escalar desde cero implica un **cold start** (descarga de imagen + boot de Node). Configurá `Startup`, `Liveness` y `Readiness`. Como esta app **no expone `/health`**, apuntamos a `/login` (página pública servida sin auth) con código esperado `200/3xx`.

> Si más adelante agregás un `app/api/health/route.ts` que devuelva `{ ok: true }`, cambiá `path: /login` por `path: /api/health` en los probes.

```yaml
probes:
  - type: Startup
    httpGet:
      path: /login
      port: 3000
    initialDelaySeconds: 5
    periodSeconds: 5
    failureThreshold: 30
    timeoutSeconds: 5
  - type: Liveness
    httpGet:
      path: /login
      port: 3000
    periodSeconds: 30
    failureThreshold: 3
    timeoutSeconds: 5
  - type: Readiness
    httpGet:
      path: /login
      port: 3000
    initialDelaySeconds: 5
    periodSeconds: 10
    failureThreshold: 3
    timeoutSeconds: 5
```

Flujo típico:

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME -o yaml > app.yaml
# editar app.yaml: añadir el bloque `probes:` bajo properties.template.containers[0]
az containerapp update -n $APP_NAME -g $RG_NAME --yaml app.yaml
```

Referencia: [Health probes in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/health-probes).

---

## 6.3 Escala: `cooldownPeriod` y `pollingInterval`

Con `minReplicas: 0`, Azure Container Apps evalúa el tráfico cada `pollingInterval` segundos y, si la métrica está por debajo del umbral durante `cooldownPeriod` segundos consecutivos, escala las réplicas a **cero**. La próxima petición vuelve a sufrir cold start (5–15 s en Next standalone, ver §8.2).

**Defaults de KEDA / ACA:** `pollingInterval=30`, `cooldownPeriod=300` (5 min).

Para este frontend usamos **`cooldownPeriod: 900`** (15 min) — el mismo valor que `DashboardBackend` — para amortiguar pausas de uso interactivo del dashboard sin pagar réplicas permanentes.

```yaml
properties:
  template:
    scale:
      minReplicas: 0
      maxReplicas: 2
      pollingInterval: 30
      cooldownPeriod: 900
```

### 6.3.1 Aplicar el cambio vía YAML (única vía soportada)

`az containerapp create/update` **no expone flags CLI** para `cooldownPeriod` ni `pollingInterval`; sólo se pueden modificar a través de `--yaml` (soporte agregado en la extensión `containerapp` por [Azure/azure-cli-extensions#8236](https://github.com/Azure/azure-cli-extensions/pull/8236), nov 2024). `--scale-cooldown-period` y `--scale-polling-interval` **no existen** y devuelven `unrecognized arguments`.

```powershell
az extension update --name containerapp

az containerapp show -n $APP_NAME -g $RG_NAME -o yaml > app.yaml
# editar app.yaml → en properties.template.scale agregar/ajustar:
#   pollingInterval: 30
#   cooldownPeriod: 900
az containerapp update -n $APP_NAME -g $RG_NAME --yaml app.yaml
```

> Si `--yaml` devuelve errores de validación tras el `show`, suele ser por campos read-only que ACA no acepta de vuelta (`id`, `systemData`, `provisioningState`, IPs de salida, `latestRevisionFqdn`, etc.). Borralos del archivo antes del `update` o trabajá con un YAML mínimo de `properties.template` siguiendo el ejemplo de [`apis/DashboardBackend/deploy/app-dashboard-probes.yaml`](../../../apis/DashboardBackend/deploy/app-dashboard-probes.yaml).

### 6.3.2 Verificar

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.scale" -o json
```

Esperado:

```json
{
  "minReplicas": 0,
  "maxReplicas": 2,
  "pollingInterval": 30,
  "cooldownPeriod": 900,
  "rules": null
}
```

> **Trade-off:** subir `cooldownPeriod` reduce cold starts visibles pero mantiene la(s) réplica(s) facturándose más tiempo tras el último request. Si la UX exige respuesta inmediata sin cold start, considerá `--min-replicas 1` en su lugar (ver §11).

Referencia: [Scaling rules in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/scale-app).

---

## 7. Red: backend del dashboard y webhook

| Destino | Verificación |
| ------- | ------------ |
| `DashboardBackend` (otra Container App) | Salida HTTPS en el mismo entorno o público. La URL pública del Dashboard Backend ya está embebida (`NEXT_PUBLIC_DASHBOARD_API_URL`). |
| Webhook n8n | Salida HTTPS al FQDN del webhook. |
| CORS | El backend Flask debe permitir el origen del nuevo FQDN del frontend. Revisá `CORS_ORIGINS` (o equivalente) en el Dashboard Backend si aparecen errores `OPTIONS`/`Access-Control-Allow-Origin`. |

**FQDN público y IPs de salida:**

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.outboundIpAddresses" -o tsv
```

---

## 8. Verificación post-deploy

### 8.1 URL pública

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
"https://$FQDN"
# Abrir en navegador o:
curl.exe -sS -I "https://$FQDN/login"
```

Esperado: `HTTP/1.1 200 OK` (página de login servida por Next.js standalone).

### 8.2 Escala (0–2)

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.scale" -o json
```

Deberías ver `"minReplicas": 0`, `"maxReplicas": 2` y `"cooldownPeriod": 900` (ver §6.3). Con tráfico nulo durante ≥ 15 min, las réplicas bajan a **cero** (cold start en la siguiente petición; típicamente 5–15 s para Next standalone en `node:22-alpine`).

### 8.3 Logs

```powershell
az containerapp logs show -n $APP_NAME -g $RG_NAME --follow
```

Buscá la línea `▲ Next.js 16.2.3 - Local: http://0.0.0.0:3000` cuando arranca.

### 8.4 Prueba funcional

1. Abrir `https://$FQDN/login` y autenticarse con un usuario válido del Dashboard Backend.
2. Verificar que `/dashboard` cargue métricas (la llamada va a `NEXT_PUBLIC_DASHBOARD_API_URL`).
3. Probar `/upload` y `/admin` según rol.

Si las métricas no cargan, abrir DevTools → Network y confirmar que las requests apuntan al FQDN del Dashboard Backend (no a `127.0.0.1:5002`). Si apuntan a `127.0.0.1`, **el bundle se construyó sin el `--build-arg`** → rebuild (§5).

---

## 8.5 Verificación local de la imagen (Docker o Podman)

Desde la raíz del repo `Tesis`:

```powershell
podman build `
  --ignorefile sources/app/olh-sentiment-ia/context.dockerignore `
  --build-arg NEXT_PUBLIC_DASHBOARD_API_URL=$DASHBOARD_API_URL `
  --build-arg NEXT_PUBLIC_DASHBOARD_HOTEL_ID=$DASHBOARD_HOTEL_ID `
  --build-arg NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL=$ANALYSIS_WEBHOOK `
  -t olh-sentiment-ia:local `
  -f sources/app/olh-sentiment-ia/Dockerfile `
  sources/app/olh-sentiment-ia

podman run --rm -p 3000:3000 -e PORT=3000 -e HOSTNAME=0.0.0.0 olh-sentiment-ia:local
```

En otra terminal: `curl.exe -I http://localhost:3000/login`.

---

## 9. Actualizar imagen (cambio de código o de URLs públicas)

### 9.1 Sólo cambió el código (las URLs siguen iguales)

Build con los **mismos** `--build-arg`, push con tag nuevo, y:

```powershell
az containerapp update --name $APP_NAME --resource-group $RG_NAME --image "$ACR_NAME.azurecr.io/olh-sentiment-ia:1.0.1"
```

### 9.2 Cambió alguna `NEXT_PUBLIC_*` (p. ej. nueva URL del backend)

**Sí o sí rebuild + push.** No alcanza con `az containerapp update --set-env-vars` porque el JS del cliente ya tiene la URL vieja embebida.

```powershell
$IMAGE_TAG = "$ACR_NAME.azurecr.io/olh-sentiment-ia:1.0.2"
$DASHBOARD_API_URL = "https://nuevo-host..."

podman build `
  --ignorefile sources/app/olh-sentiment-ia/context.dockerignore `
  --build-arg NEXT_PUBLIC_DASHBOARD_API_URL=$DASHBOARD_API_URL `
  --build-arg NEXT_PUBLIC_DASHBOARD_HOTEL_ID=$DASHBOARD_HOTEL_ID `
  --build-arg NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL=$ANALYSIS_WEBHOOK `
  -t $IMAGE_TAG `
  -f sources/app/olh-sentiment-ia/Dockerfile `
  sources/app/olh-sentiment-ia

podman push $IMAGE_TAG
az containerapp update --name $APP_NAME --resource-group $RG_NAME --image $IMAGE_TAG
```

### 9.3 Forzar nueva revisión (sin cambiar imagen)

```powershell
az containerapp revision restart -n $APP_NAME -g $RG_NAME
```

---

## 10. Archivos relacionados en el repo

| Archivo | Uso |
| ------- | --- |
| [`Dockerfile`](../Dockerfile) | Imagen multi-stage Node 22 + Next standalone (contexto: la propia carpeta del frontend). |
| [`context.dockerignore`](../context.dockerignore) | Excluye `node_modules/`, `.next/`, `.env*`, `.git`, etc. Pasar como `--ignorefile` (ver §5). |
| [`next.config.ts`](../next.config.ts) | Define `output: "standalone"` (necesario para `node server.js`). |
| [`.env copy.example`](../.env%20copy.example) | Plantilla de variables `NEXT_PUBLIC_*`. |

---

## 11. Riesgos y problemas frecuentes

- **Bundle apunta a `127.0.0.1`:** olvidaste `--build-arg NEXT_PUBLIC_DASHBOARD_API_URL=...`. Rebuild.
- **CORS desde el navegador:** el Dashboard Backend rechaza el nuevo FQDN. Añadilo a la allowlist del backend.
- **Cookies / login** no persisten: el dominio cambió respecto al desarrollo local. Verificá `Secure`/`SameSite` de la cookie `access_token` y que el frontend y backend compartan esquema HTTPS.
- **Cold start molesto** con `minReplicas=0`: como mitigación intermedia, subí `cooldownPeriod` (§6.3) para que las réplicas tarden más en bajar a cero. Si la UX sigue sin tolerarlo, pasá a `--min-replicas 1` (deja de costar “a cero” pero garantiza respuesta inmediata).
- **`next/font/google` falla en build:** Podman Machine sin red → `next build` no descarga las fuentes. Probá `podman machine ssh -- ping 8.8.8.8`.
- **Memoria insuficiente en build:** Next 16 + React 19 puede pedir > 1 GB durante el build. Si tu máquina es limitada, subí la RAM de Podman Machine (`podman machine set --memory 4096`).
