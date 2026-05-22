# Despliegue en Azure Container Apps

- Guía paso a paso (incluye reutilizar RG, ACR, Log Analytics y entorno ACA de Data Verification Cleaner): [`../../docs/DEPLOY_AZURE_ACA.md`](../../docs/DEPLOY_AZURE_ACA.md)
- Plantilla YAML (completar IDs y nombres): [`container-app.template.yaml`](container-app.template.yaml)

Aplicar la plantilla (tras reemplazar marcadores):

```bash
az containerapp create --resource-group "<RESOURCE_GROUP_NAME>" --yaml container-app.template.yaml
```
