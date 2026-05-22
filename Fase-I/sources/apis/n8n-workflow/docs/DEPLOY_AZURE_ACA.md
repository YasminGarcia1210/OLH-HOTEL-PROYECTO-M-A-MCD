# Guía: Azure Container Apps para n8n (workflow OLH Hoteles ICESI)

Esta guía describe cómo **desplegar n8n** en **Azure Container Apps (ACA)** con **imagen en ACR**, **variables de entorno** alineadas con `[../.env.example](../.env.example)` y el workflow `[../miaa-Olh-hoteles-icesi.json](../miaa-Olh-hoteles-icesi.json)` (nodos HTTP y Gmail leen URLs y destinatarios desde `$env`).

Incluye **Azure Files** montado como volumen compartido del entorno para persistir datos de n8n bajo `/home/node/.n8n`, y comandos para **PowerShell** y **Podman** (build/push).

**No pegues credenciales en Git.** Usá el Portal, Azure CLI o Key Vault para secretos (`N8N_ENCRYPTION_KEY`, claves de Storage, contraseña de PostgreSQL si aplica).

---

## Convenciones: Bash vs PowerShell (Windows)

Igual que en `[DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md)`:

| Bash                             | PowerShell                                                |
| -------------------------------- | --------------------------------------------------------- |
| `export NAME="valor"`            | `$NAME = "valor"`                                         |
| Continuar línea con `\`          | Continuar con **acento grave** `` ` `` al final de la línea |
| `VAR=$(az ... -o tsv)`           | `$VAR = az ... -o tsv`                                    |

**Cadenas con `&`:** en PowerShell usá **comillas simples** o *here-string* (ver la guía de DataVerification).

**`curl` en Windows:** usá `curl.exe` o `Invoke-RestMethod`.

**Azure CLI:** extensión Container Apps: `az extension add --name containerapp` (y actualizarla con frecuencia).

---

## 0. Réplicas, SQLite y volumen compartido (importante)

| Escenario | Recomendación |
| --------- | ------------- |
| **1 réplica** (`minReplicas` = `maxReplicas` = 1) y volumen **Azure Files** en `/home/node/.n8n` | Válido para laboratorio o carga baja. SQLite sobre SMB puede tener **mayor latencia** o problemas de bloqueo en escenarios exigentes; monitoreá logs. |
| **Varias réplicas** | **No** uses SQLite compartido. Configurá **PostgreSQL** para n8n (`DB_TYPE=postgresdb` y variables `DB_POSTGRESDB_*`) y, si necesitás alta disponibilidad entre instancias, revisá la documentación oficial de n8n sobre **queue mode** y ejecutores. |

Un **Azure File Share** sí permite que **varias réplicas monten el mismo recurso** (SMB), pero **n8n con SQLite en ese volumen no es adecuado para varios procesos escribiendo a la vez**. Si necesitás más de una réplica, la base de datos del editor debe ser **PostgreSQL** (u otra BD soportada), no el `database.sqlite` compartido.

---

## 1. Prerrequisitos

| Requisito | Notas |
| --------- | ----- |
| Suscripción Azure | Rol típico: **Contributor** en el grupo de recursos. |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) + extensión `containerapp` | |
| **Podman** (o Docker) | Build y push hacia ACR. |
| Grupo de recursos, ACR, Log Analytics, **Container Apps Environment** | Podés **reutilizar** los mismos nombres que en otros servicios del pipeline (`miaa-tg-olh-sentiment-analysis`, `acrolhpipeline`, `cae-olh-pipeline`, etc.). |
| **Storage Account** + **File share** | Para el volumen persistente de n8n. |

Iniciá sesión:

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

---

## 2. Mapa de variables de entorno

### 2.1 Pipeline (consumidas por el workflow vía `$env`)

| Variable | Contenido |
| -------- | --------- |
| `SVC_DATA_VERIFICATION_URL_EJECUTAR` | URL completa `POST .../api/v1/verificacion/ejecutar` |
| `SVC_SENTIMENT_URL_PROCESAR` | URL completa `POST .../api/v1/sentimiento/procesar` |
| `SVC_SENTIMENT_API_BASE` | Base `https://.../api/v1/sentimiento` (sin `/archivo/`; el workflow concatena `/archivo/{id}/resultados`) |
| `SVC_ABSA_URL_PROCESAR_BATCH` | URL completa `POST .../api/v1/absa/procesar-batch` |
| `SVC_ABSA_URL_BATCH_SINCRONIZAR` | URL completa `POST .../api/v1/absa/batch/sincronizar` |
| `SVC_METRIC_PROCESSOR_URL_CALCULAR` | URL completa `POST .../api/v1/metricas/calcular` |
| `OLH_PIPELINE_NOTIFY_RECIPIENTS` | Lista de correos separados por **coma** (sin espacios recomendado), p. ej. `a@x.com,b@y.com` |

### 2.2 n8n / HTTPS / webhooks

| Variable | ¿Secreto? | Descripción |
| -------- | --------- | ----------- |
| `N8N_ENCRYPTION_KEY` | **Sí** | Cifrado de credenciales en la base interna de n8n. Generá una clave aleatoria (p. ej. 32 bytes hex). **Si la perdés, no podrás descifrar credenciales existentes.** |
| `N8N_HOST` | No | FQDN público de la app (sin `https://`). |
| `N8N_PROTOCOL` | No | `https` detrás del ingress de ACA. |
| `N8N_PORT` | No | `5678` (puerto interno del contenedor n8n). |
| `WEBHOOK_URL` | No | URL base pública, p. ej. `https://<fqdn-de-tu-app>/` — necesaria para **Webhook** y nodos **Wait** que reanudan por URL. |
| `N8N_SECURE_COOKIE` | No | `true` cuando servís por HTTPS. |
| `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS` | No | En volúmenes **Azure Files** (SMB) los archivos suelen verse con permisos **0777**; n8n lo advierte y, en versiones recientes, puede intentar endurecer permisos de forma poco fiable sobre SMB. Para ACA con montaje en `/home/node/.n8n`, usá **`false`** (laboratorio) salvo que migres a un backend donde `chmod` sea coherente. Ver [variables de seguridad](https://docs.n8n.io/hosting/configuration/environment-variables/security/). |
| `N8N_BLOCK_ENV_ACCESS_IN_NODE` | No | Para el workflow con **`$env.SVC_*`**, debe ser **`false`** (permitir leer variables de entorno en expresiones y Code). Si es **`true`**, verás *access to env vars denied* y el flujo no podrá resolver URLs. [Documentación](https://docs.n8n.io/hosting/configuration/environment-variables/security/). |

Las credenciales **Gmail OAuth2** no van en variables de entorno: se guardan en la BD de n8n tras configurarlas en el editor (una vez importado el workflow).

### 2.3 Opcional: PostgreSQL para n8n (varias réplicas)

| Variable | Descripción |
| -------- | ----------- |
| `DB_TYPE` | `postgresdb` |
| `DB_POSTGRESDB_HOST`, `DB_POSTGRESDB_PORT`, `DB_POSTGRESDB_DATABASE`, `DB_POSTGRESDB_USER`, `DB_POSTGRESDB_PASSWORD` | Conexión a Azure PostgreSQL Flexible / Neon / similar. Podés usar la **misma base** que las APIs (`olh_sentiment`, etc.) si separás datos con un schema dedicado. |
| `DB_POSTGRESDB_SCHEMA` | Opcional; default `public`. Si en Neon creaste un schema aparte (p. ej. `n8n`), poné ese nombre para que las tablas y migraciones de n8n no mezclen con el schema de las APIs. |
| `DB_POSTGRESDB_SSL_ENABLED` | `true` en Neon y la mayoría de Postgres en la nube. |

En Neon, el rol que usa n8n necesita al menos `USAGE` y `CREATE` en ese schema (y permisos sobre tablas/secuencias que cree n8n). Ejemplo en SQL Editor (sustituí `tu_usuario`):

```sql
CREATE SCHEMA IF NOT EXISTS n8n;
GRANT USAGE, CREATE ON SCHEMA n8n TO tu_usuario;
ALTER DEFAULT PRIVILEGES IN SCHEMA n8n GRANT ALL ON TABLES TO tu_usuario;
ALTER DEFAULT PRIVILEGES IN SCHEMA n8n GRANT ALL ON SEQUENCES TO tu_usuario;
```

Con Postgres, el volumen Azure Files puede usarse solo para **adjuntos / binary data** (`N8N_BINARY_DATA_STORAGE_PATH`) si lo necesitás, o podés operar sin montaje extra según volumen de archivos.

---

## 3. Nombres de ejemplo (PowerShell)

Ajustá a tu suscripción. Si ya tenés RG, CAE y ACR del pipeline, **reutilizá** esos valores y omití los `create` duplicados.

```powershell
$LOCATION = "eastus2"
$RG_NAME = "miaa-tg-olh-sentiment-analysis"
$ACR_NAME = "acrolhpipeline"
$LAW_NAME = "law-olh-pipeline"
$CAE_NAME = "cae-olh-pipeline"
$APP_NAME = "n8n-olh-pipeline"

# Storage dedicado al share de n8n (nombre globalmente único)
$STORAGE_ACCOUNT = "stn8nolh$(Get-Random -Maximum 99999)"
$SHARE_NAME = "n8n-data"
$ENV_STORAGE_NAME = "n8n-azurefiles"
```

Si el grupo de recursos o el entorno ACA **ya existen**, no vuelvas a crearlos; continuá desde la sección que corresponda.

---

## 4. Infraestructura: Storage Account y File share

```powershell
az group create --name $RG_NAME --location $LOCATION

az storage account create `
  --name $STORAGE_ACCOUNT `
  --resource-group $RG_NAME `
  --location $LOCATION `
  --sku Standard_LRS

az storage share create `
  --name $SHARE_NAME `
  --account-name $STORAGE_ACCOUNT

$ST_KEY = az storage account keys list -g $RG_NAME -n $STORAGE_ACCOUNT --query "[0].value" -o tsv
```

---

## 5. Registrar el share en el Container Apps Environment

El entorno `$CAE_NAME` debe existir (como en la guía de DataVerification: Log Analytics + `az containerapp env create`). Luego **vinculá** el Azure Files al entorno con un nombre lógico (`$ENV_STORAGE_NAME`):

```powershell
az containerapp env storage set `
  -n $CAE_NAME `
  -g $RG_NAME `
  --storage-name $ENV_STORAGE_NAME `
  --azure-file-account-name $STORAGE_ACCOUNT `
  --azure-file-account-key $ST_KEY `
  --azure-file-share-name $SHARE_NAME `
  --access-mode ReadWrite
```

Comprobación:

```powershell
az containerapp env storage list -n $CAE_NAME -g $RG_NAME -o table
```

---

## 6. Construir y publicar la imagen (Podman + PowerShell)

Contexto: **raíz del monorepo Tesis** (donde está `sources/`).

### 6.1 Login a ACR con Podman

`az acr login` a veces falla sin Docker; usá token:

```powershell
az acr login -n $ACR_NAME --expose-token
# En la salida: loginServer, username, accessToken

podman login <loginServer> -u <username> -p "<accessToken>"
```

### 6.2 Build y push

```powershell
$IMAGE_TAG = "$ACR_NAME.azurecr.io/n8n-olh-pipeline:1.0.0"
podman build -t $IMAGE_TAG -f sources/apis/n8n-workflow/Dockerfile sources/apis/n8n-workflow
podman push $IMAGE_TAG
```

---

## 7. Crear la Container App (y luego volumen + URL pública)

La CLI `az containerapp create` no expone de forma estable todos los campos de **volúmenes AzureFile** en un solo comando; el flujo recomendado es **crear** la app y luego **actualizar con YAML** para el montaje (o usar el Portal: **Volumes**).

### 7.1 Variables del pipeline y clave de cifrado (antes del `create`)

Definí las URLs (podés copiarlas desde `[../.env.example](../.env.example)`):

```powershell
$SVC_DATA_VERIFICATION_URL_EJECUTAR = "https://data-verification-cleaner.nicehill-77407515.eastus2.azurecontainerapps.io/api/v1/verificacion/ejecutar"
$SVC_SENTIMENT_URL_PROCESAR = "https://sentiment-prediction.nicehill-77407515.eastus2.azurecontainerapps.io/api/v1/sentimiento/procesar"
$SVC_SENTIMENT_API_BASE = "https://sentiment-prediction.nicehill-77407515.eastus2.azurecontainerapps.io/api/v1/sentimiento"
$SVC_ABSA_URL_PROCESAR_BATCH = "https://absa-service.nicehill-77407515.eastus2.azurecontainerapps.io/api/v1/absa/procesar-batch"
$SVC_ABSA_URL_BATCH_SINCRONIZAR = "https://absa-service.nicehill-77407515.eastus2.azurecontainerapps.io/api/v1/absa/batch/sincronizar"
$SVC_METRIC_PROCESSOR_URL_CALCULAR = "https://metric-processor.nicehill-77407515.eastus2.azurecontainerapps.io/api/v1/metricas/calcular"
$OLH_PIPELINE_NOTIFY_RECIPIENTS = "rchicangana@gmail.com,lauraichaparro11@gmail.com,fabianortiz.iet@gmail.com"
```

Generá `N8N_ENCRYPTION_KEY` (no la guardes en Git):

```powershell
$N8N_ENC = -join ((1..32) | ForEach-Object { "{0:x2}" -f (Get-Random -Maximum 256) })
# Alternativa: openssl rand -hex 32
```

### 7.2 Creación inicial (sin volumen todavía; 1 réplica; ingress HTTPS; secretos y env)

Ajustá credenciales de ACR como en la guía de DataVerification (admin del ACR o identidad administrada + `AcrPull`).

`N8N_HOST` y `WEBHOOK_URL` dependen del **FQDN** que Azure asigna al crear el ingress; las definimos en el paso **7.3** tras el `create`.

```powershell
az acr update -n $ACR_NAME --admin-enabled true
$ACR_USER = az acr credential show -n $ACR_NAME --query username -o tsv
$ACR_PASS = az acr credential show -n $ACR_NAME --query "passwords[0].value" -o tsv

az containerapp create `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --environment $CAE_NAME `
  --image "$ACR_NAME.azurecr.io/n8n-olh-pipeline:1.0.0" `
  --registry-server "$ACR_NAME.azurecr.io" `
  --registry-username $ACR_USER `
  --registry-password $ACR_PASS `
  --target-port 5678 `
  --ingress external `
  --min-replicas 1 `
  --max-replicas 1 `
  --cpu 1.0 `
  --memory 2.0Gi `
  --secrets "n8n-encryption-key=$N8N_ENC" `
  --env-vars `
    "N8N_ENCRYPTION_KEY=secretref:n8n-encryption-key" `
    "N8N_PROTOCOL=https" `
    "N8N_PORT=5678" `
    "N8N_SECURE_COOKIE=true" `
    "N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false" `
    "N8N_BLOCK_ENV_ACCESS_IN_NODE=false" `
    "SVC_DATA_VERIFICATION_URL_EJECUTAR=$SVC_DATA_VERIFICATION_URL_EJECUTAR" `
    "SVC_SENTIMENT_URL_PROCESAR=$SVC_SENTIMENT_URL_PROCESAR" `
    "SVC_SENTIMENT_API_BASE=$SVC_SENTIMENT_API_BASE" `
    "SVC_ABSA_URL_PROCESAR_BATCH=$SVC_ABSA_URL_PROCESAR_BATCH" `
    "SVC_ABSA_URL_BATCH_SINCRONIZAR=$SVC_ABSA_URL_BATCH_SINCRONIZAR" `
    "SVC_METRIC_PROCESSOR_URL_CALCULAR=$SVC_METRIC_PROCESSOR_URL_CALCULAR" `
    "OLH_PIPELINE_NOTIFY_RECIPIENTS=$OLH_PIPELINE_NOTIFY_RECIPIENTS"
```

### 7.3 FQDN, `N8N_HOST` y `WEBHOOK_URL`

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
$WEBHOOK_BASE = "https://$FQDN/"

az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --set-env-vars "N8N_HOST=$FQDN" "WEBHOOK_URL=$WEBHOOK_BASE"
```

### 7.4 Montar Azure Files en `/home/node/.n8n`

Exportá el recurso a YAML:

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME -o yaml > n8n-aca.yaml
```

Editá `n8n-aca.yaml` en un editor y, bajo `properties.template`, asegurá:

1. **`volumes`** (hermano de `containers`, mismo nivel dentro de `template`):

```yaml
  template:
    volumes:
      - name: n8n-user-data
        storageType: AzureFile
        storageName: n8n-azurefiles
```

`storageName` debe ser **exactamente** el `--storage-name` usado en `az containerapp env storage set` (`$ENV_STORAGE_NAME`).

2. **`volumeMounts`** dentro del contenedor n8n (mismo nivel que `env`, `image`, `resources`):

```yaml
        volumeMounts:
          - mountPath: /home/node/.n8n
            volumeName: n8n-user-data
```

Guardá el archivo y aplicá:

```powershell
az containerapp update --name $APP_NAME --resource-group $RG_NAME --yaml n8n-aca.yaml
```

Si Azure CLI rechaza propiedades de solo lectura del `show`, borrá del YAML secciones como `status`, `id` de recursos hijos o usá una plantilla mínima según [Actualizar con YAML](https://learn.microsoft.com/azure/container-apps/azure-resource-manager-api-version). Referencia de estructura: `[../deploy/aca/container-app.template.yaml](../deploy/aca/container-app.template.yaml)`.

Si **ya creaste** la app sin esa variable, agregala (mismo valor que en el `create`):

```powershell
az containerapp update `
  --name $APP_NAME `
  --resource-group $RG_NAME `
  --set-env-vars "N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false"
```

O sumala al bloque `env:` del YAML antes de `az containerapp update --yaml`.

### 7.5 Si el contenedor falla al abrir la UI (paso 8): interpretar logs

Es frecuente ver en **Log stream** o `az containerapp logs show`:

1. **`Permissions 0777 for n8n settings file .../config`** — Viene del **Azure File Share** (SMB): el sistema de archivos no expone permisos UNIX como un disco local. No es por sí solo el error fatal; mitigación: `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false` (tabla §2.2 y variable en §7.2 / YAML).

2. **`Last session crashed`** — n8n detecta que la sesión anterior no cerró limpio (nuevo despliegue, reinicio del réplica, SIGKILL por **OOM**, etc.). En muchos arranques **la UI sigue funcionando** tras ese mensaje. Si la réplica queda en **Failed** o hay reinicios en bucle, el motivo real suele estar **después** en los mismos logs: buscá `SQLITE`, `database is locked`, `EACCES`, `out of memory` o trazas `Error:`.

3. **`DeprecationWarning: punycode`** — Aviso de Node.js; no explica caídas del contenedor.

Para ver el final del arranque (donde suele estar el fallo):

```powershell
az containerapp logs show -n $APP_NAME -g $RG_NAME --tail 300
```

Si aparecen errores de **SQLite** sobre el volumen compartido, revisá §0 (una réplica y límites de SQLite/SMB) o migrá a **PostgreSQL** (§2.3). Si cambiaste `N8N_ENCRYPTION_KEY` entre revisiones con datos ya guardados en el share, el arranque puede romperse por credenciales/BD cifrada inconsistente: mantené la misma clave o empezá con un share vacío (solo en entornos de prueba).

4. **`There was an error running database migrations`** + **`SQLITE_BUSY: database is locked`** — Es el conflicto típico **SQLite + Azure Files (SMB)**: el bloqueo de archivos sobre red no es fiable para la BD embebida de n8n, y las **migraciones** al arranque empeoran la condición de carrera. **No se soluciona** de forma estable solo con más CPU/memoria.

   **Mitigación rápida (a veces ayuda durante un deploy):** asegurate de **una sola revisión activa** (`activeRevisionsMode: Single` en el YAML o en el Portal) y desactivá revisiones viejas que sigan con tráfico:

   ```powershell
   az containerapp revision list -n $APP_NAME -g $RG_NAME -o table
   az containerapp revision deactivate -n $APP_NAME -g $RG_NAME --revision <nombre-revision-antigua>
   ```

   Si el error **vuelve** al reiniciar, la solución correcta es **mover la BD de n8n a PostgreSQL** (§2.3): SQLite debe dejar de vivir en el share montado. Tras configurar `DB_TYPE=postgresdb` y las variables `DB_POSTGRESDB_*`, n8n usa Postgres para datos editoriales; el volumen Azure Files puede quedar para binarios (`N8N_BINARY_DATA_STORAGE_PATH`) si lo necesitás, o podés simplificar y operar sin montaje extra según uso.

   **Solo laboratorio (se pierden datos de n8n en el share):** vaciar el file share o borrar `database.sqlite` en el share con la app detenida puede destrabar un lock persistente corrupto; **no** lo hagas si ya tenés workflows o credenciales que querés conservar sin backup.

### 7.6 Paso a paso: Neon (misma base que las APIs) + schema `n8n`

Objetivo: que n8n deje de usar **SQLite** en Azure Files y use **PostgreSQL en Neon**, con tablas en el schema **`n8n`** y la misma base que usan DataVerification / MetricProcessor / etc. (ej. `olh_sentiment`).

**Paso 1 — Variables de PowerShell (ajustá valores reales)**

Usá los mismos host, puerto, nombre de base, usuario y contraseña que ya funcionan en una API (por ejemplo `[../../MetricProcessor/.env.example](../../MetricProcessor/.env.example)` o tu `.env` local **sin commitear**). Ejemplo:

```powershell
$RG_NAME  = "miaa-tg-olh-sentiment-analysis"
$APP_NAME = "n8n-olh-pipeline"

# Copiados de Neon / .env de las APIs (sin contraseña en el historial de Git)
$PG_HOST     = "tu-host.region.aws.neon.tech"   # mismo que DB_HOST o host del DATABASE_URL
$PG_PORT     = "5432"
$PG_DATABASE = "olh_sentiment"                  # mismo DB_NAME que las APIs
$PG_USER     = "tu_usuario_neon"
$PG_SCHEMA   = "n8n"
```

**Paso 2 — Permisos en Neon (SQL Editor)**

Sustituí `tu_usuario_neon` por el rol real (el de `$PG_USER`). Ejecutá:

```sql
CREATE SCHEMA IF NOT EXISTS n8n;
GRANT USAGE, CREATE ON SCHEMA n8n TO tu_usuario_neon;
ALTER DEFAULT PRIVILEGES IN SCHEMA n8n GRANT ALL ON TABLES TO tu_usuario_neon;
ALTER DEFAULT PRIVILEGES IN SCHEMA n8n GRANT ALL ON SEQUENCES TO tu_usuario_neon;
```

**Paso 3 — (Recomendado) Quitar SQLite viejo del Azure File Share**

Con **0 réplicas** nadie mantiene abierto `database.sqlite`:

```powershell
az containerapp update -n $APP_NAME -g $RG_NAME --min-replicas 0 --max-replicas 0
```

En el **Portal** → Storage del pipeline → **File shares** → tu share de n8n → eliminá `database.sqlite` si existe (solo datos locales de n8n en SQLite; si no existe, seguí al paso 4).

```powershell
az containerapp update -n $APP_NAME -g $RG_NAME --min-replicas 1 --max-replicas 1
```

**Paso 4 — Secreto en ACA para la contraseña de Postgres**

No pegues la contraseña en el YAML del repo. En una consola **local** (PowerShell), definí la contraseña solo en memoria y registrá el secreto en el recurso:

```powershell
$PG_PASSWORD = Read-Host -AsSecureString "Contraseña Neon (misma que las APIs)"
$BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($PG_PASSWORD)
$PG_PASS_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

az containerapp secret set `
  -n $APP_NAME `
  -g $RG_NAME `
  --secrets "neon-n8n-db-password=$PG_PASS_PLAIN"

Remove-Variable PG_PASS_PLAIN, PG_PASSWORD, BSTR -ErrorAction SilentlyContinue
```

Si preferís no usar `Read-Host`, podés armar el `secret set` una sola vez a mano sin guardar el valor en archivos.

**Paso 5 — Variables de entorno de n8n hacia Neon**

Un solo `update` conexiona la app (la contraseña referencia el secreto `neon-n8n-db-password`):

```powershell
az containerapp update `
  -n $APP_NAME `
  -g $RG_NAME `
  --set-env-vars `
    "DB_TYPE=postgresdb" `
    "DB_POSTGRESDB_HOST=$PG_HOST" `
    "DB_POSTGRESDB_PORT=$PG_PORT" `
    "DB_POSTGRESDB_DATABASE=$PG_DATABASE" `
    "DB_POSTGRESDB_USER=$PG_USER" `
    "DB_POSTGRESDB_PASSWORD=secretref:neon-n8n-db-password" `
    "DB_POSTGRESDB_SCHEMA=$PG_SCHEMA" `
    "DB_POSTGRESDB_SSL_ENABLED=true"
```

**Paso 6 — Reinicio y logs**

```powershell
$REV = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.latestRevisionName" -o tsv
az containerapp revision restart -n $APP_NAME -g $RG_NAME --revision $REV

az containerapp logs show -n $APP_NAME -g $RG_NAME --tail 200
```

Esperable: arranque sin `SQLITE_BUSY`; la primera vez n8n crea tablas en el schema `n8n`. Si falla por **SSL** o **conexión**, compará host/puerto con los de una API que sí conecte (Neon “direct” vs “pooler” según tu proyecto).

**Paso 7 — IP allowlist en Neon (si la activaste)**

Si en Neon restringiste por IP, los Container Apps salen por muchas IPs salientes; permití el acceso según la política de Neon o la [guía de red del pipeline](../../DataVerificationCleanner/docs/DEPLOY_AZURE_ACA.md) (sección Neon / allowlist).

**Paso 8 — UI y workflow**

Continuá con **[§8](#8-importar-el-workflow-y-credencial-gmail)** (abrir `https://$FQDN/`, importar workflow, Gmail).

---

## 8. Importar el workflow y credencial Gmail

1. Abrí `https://$FQDN/` (usuario inicial de n8n se define en primer arranque según versión; en despliegues nuevos puede pedirse **owner** por UI). Si la app no responde o el contenedor figura en fallo, revisá **§7.5** y los logs con `--tail`.
2. **Import** el archivo `[../miaa-Olh-hoteles-icesi.json](../miaa-Olh-hoteles-icesi.json)`.
3. Configurá la credencial **Gmail OAuth2** en n8n (consola Google Cloud: OAuth client, redirect URI de n8n).
4. Activá el workflow y probá el **Webhook** con la URL que muestra n8n (debe alinearse con `WEBHOOK_URL`).

Los nodos HTTP ya usan `$env.SVC_*` y Gmail `sendTo` usa `$env.OLH_PIPELINE_NOTIFY_RECIPIENTS`.

### 8.1 Gmail OAuth: error **431** (“authorization URL” / header fields too large)

**431** indica cabeceras HTTP demasiado grandes, no un fallo típico de Google OAuth en sí.

1. **Redirección en Google Cloud:** el URI debe coincidir **exactamente** con el que muestra n8n, suele ser  
   `https://<TU-FQDN>/rest/oauth2-credential/callback`  
   (sin barra extra rara; si servís n8n en subpath, incluí ese path también).

2. **Variables públicas:** `N8N_PROTOCOL=https`, `N8N_HOST=<fqdn>` (sin `https://`), `WEBHOOK_URL=https://<fqdn>/` — si alguna apunta a `http` o a otro host, el flujo OAuth puede romperse o repetirse.

3. **Navegador:** borrá **cookies y datos del sitio** solo para el dominio de tu Container App, o probá **ventana privada**. Sesiones largas o varios intentos de OAuth inflan la cookie y disparan 431.

4. **Límite de tamaño de cabeceras en Node (ACA):** si tras limpiar cookies sigue el 431, subí el límite en la Container App (una línea de env):

   ```powershell
   az containerapp update `
     -n $APP_NAME `
     -g $RG_NAME `
     --set-env-vars 'NODE_OPTIONS=--max-http-header-size=65536'
   ```

   Reiniciá la revisión si hace falta y volvé a crear la credencial Gmail.

Referencias: [GitHub n8n — 431 y payload/header](https://github.com/n8n-io/n8n/issues/7083), [OAuth redirect en docs](https://docs.n8n.io/integrations/builtin/credentials/google/oauth-generic/).

### 8.2 Nodos con `$env`: *access to env vars denied*

El workflow `miaa-Olh-hoteles-icesi` usa expresiones tipo `$env.SVC_*`. Eso exige que la instancia **permita** leer variables de entorno en nodos.

1. **Variable:** `N8N_BLOCK_ENV_ACCESS_IN_NODE` debe ser **`false`**.  
   - Si es **`true`** (o si en la **UI** de n8n activaste “block env access” en la política de seguridad), verás *ERROR: access to env vars denied* al abrir o ejecutar el nodo.

2. **Aplicar en ACA** (si aún no está en el `create` / YAML):

   ```powershell
   az containerapp update `
     -n $APP_NAME `
     -g $RG_NAME `
     --set-env-vars "N8N_BLOCK_ENV_ACCESS_IN_NODE=false"
   ```

3. **Solo en el editor:** a veces el **preview** de expresiones sigue mostrando un aviso parecido porque el editor no inyecta tu `process.env` completo; probá **ejecutar** el nodo o el workflow: en ejecución, con `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`, las variables `SVC_*` y `OLH_PIPELINE_*` deberían resolverse.

---

## 9. Verificación post-deploy

```powershell
$FQDN = az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv
curl.exe -sS -o NUL -w "%{http_code}" "https://$FQDN/"
```

Esperable: respuesta HTTP **200** o redirección a la UI de n8n.

Logs:

```powershell
az containerapp logs show -n $APP_NAME -g $RG_NAME --follow
```

Réplicas (con `min=max=1`):

```powershell
az containerapp show -n $APP_NAME -g $RG_NAME --query "properties.template.scale" -o json
```

---

## 10. Prueba local con Podman (sin Azure)

Desde la raíz del monorepo, con un archivo `.env` local (no commitear) basado en `[../.env.example](../.env.example)`:

```powershell
podman build -t n8n-olh:local -f sources/apis/n8n-workflow/Dockerfile sources/apis/n8n-workflow

podman run --rm -p 5678:5678 --env-file sources/apis/n8n-workflow/.env n8n-olh:local
```

Para probar **persistencia** como en ACA:

```powershell
New-Item -ItemType Directory -Force -Path "$env:TEMP\n8n-local-data" | Out-Null
podman run --rm -p 5678:5678 --env-file sources/apis/n8n-workflow/.env -v "${env:TEMP}/n8n-local-data:/home/node/.n8n" n8n-olh:local
```

En Windows con Podman machine, verificá que el volumen sea legible dentro de la VM (ruta WSL2 vs ruta host según tu instalación).

---

## 11. Actualizar imagen

El `[../Dockerfile](../Dockerfile)` usa `n8nio/n8n:latest`: cada **build con `--pull`** trae la última versión publicada en Docker Hub en ese momento. Sin `--pull`, Podman puede reusar capas viejas y seguirías con una versión anterior.

```powershell
$IMAGE_TAG = "$ACR_NAME.azurecr.io/n8n-olh-pipeline:1.0.1"
podman pull docker.io/n8nio/n8n:latest
podman build --pull -t $IMAGE_TAG -f sources/apis/n8n-workflow/Dockerfile sources/apis/n8n-workflow
podman push $IMAGE_TAG
az containerapp update --name $APP_NAME --resource-group $RG_NAME --image $IMAGE_TAG
```

Subí el número de tag (`1.0.2`, etc.) si querés distinguir despliegues en ACR; lo importante para la versión de n8n es el contenido del build tras `pull`.

Antes de actualizar en producción, revisá [releases de n8n](https://github.com/n8n-io/n8n/releases) por cambios que afecten workflows o migraciones de BD.

---

## 12. Archivos relacionados

| Archivo | Uso |
| ------- | --- |
| `[../Dockerfile](../Dockerfile)` | Imagen basada en `n8nio/n8n` para ACR. |
| `[../.env.example](../.env.example)` | Nombres y ejemplos de variables. |
| `[../miaa-Olh-hoteles-icesi.json](../miaa-Olh-hoteles-icesi.json)` | Workflow exportado (`$env` para URLs y destinatarios). |
| `[../deploy/aca/container-app.template.yaml](../deploy/aca/container-app.template.yaml)` | Referencia de `volumes` / `volumeMounts`. |

Documentación útil: [n8n hosting environment variables](https://docs.n8n.io/hosting/configuration/environment-variables/), [Azure Container Apps storage mounts](https://learn.microsoft.com/azure/container-apps/storage-mounts).
