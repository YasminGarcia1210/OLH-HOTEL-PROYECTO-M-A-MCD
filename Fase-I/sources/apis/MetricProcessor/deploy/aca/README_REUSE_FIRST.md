# Despliegue ACA (reuse-first) — MetricProcessor

- Guía paso a paso: [`../../docs/DEPLOY_AZURE_ACA_REUSE_FIRST.md`](../../docs/DEPLOY_AZURE_ACA_REUSE_FIRST.md)
- Plantilla YAML: [`container-app.reuse-first.template.yaml`](container-app.reuse-first.template.yaml)

## Secretos antes de aplicar YAML

La plantilla usa `secretRef` para `secret-key` y `db-password`. Creálos en la app:

```powershell
az containerapp secret set -n "<APP_NAME>" -g "<RESOURCE_GROUP_NAME>" --secrets "secret-key=..." "db-password=..."
```

## Aplicar plantilla

Desde esta carpeta (`deploy/aca`), con marcadores reemplazados:

```powershell
az containerapp create --resource-group "<RESOURCE_GROUP_NAME>" --yaml container-app.reuse-first.template.yaml
```

Si la app ya existe:

```powershell
az containerapp update --resource-group "<RESOURCE_GROUP_NAME>" --name "<APP_NAME>" --yaml container-app.reuse-first.template.yaml
```

Registro ACR: configurá credenciales o identidad administrada según tu política (la guía CLI incluye un ejemplo con admin user).
