# Despliegue en Azure Container Apps

- Guía paso a paso (PowerShell, Podman, secretos, escala 0–5, puerto 5002): [`../../docs/DEPLOY_AZURE_ACA.md`](../../docs/DEPLOY_AZURE_ACA.md)
- Plantilla YAML (completar IDs y nombres): [`container-app.template.yaml`](container-app.template.yaml)

Build de imagen (desde la raíz del repo `Tesis`; el `--ignorefile` evita enviar todo el monorepo como contexto):

```powershell
podman build `
  --ignorefile sources/apis/DashboardBackend/context.dockerignore `
  -t "<ACR>.azurecr.io/dashboard-backend:1.0.0" `
  -f sources/apis/DashboardBackend/Dockerfile sources
```

Aplicar la plantilla (tras reemplazar marcadores):

```bash
az containerapp create --resource-group "<RESOURCE_GROUP_NAME>" --yaml container-app.template.yaml
```

Desde esta carpeta, si usás ruta relativa al archivo:

```powershell
az containerapp create --resource-group $RG_NAME --yaml ./container-app.template.yaml
```
