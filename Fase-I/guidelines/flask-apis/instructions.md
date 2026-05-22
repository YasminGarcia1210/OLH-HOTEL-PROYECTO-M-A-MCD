# Instrucciones: construir o extender APIs Flask en este monorepo

Este documento es la guía operativa complementaria de **[guidelines.md](guidelines.md)**. Usa **[DataVerificationCleanner](../../sources/apis/DataVerificationCleanner/)** como plantilla viva.

---

## 1. Crear un nuevo servicio Flask

1. **Carpeta** bajo `sources/apis/<NombreServicio>/` (nombre en PascalCase o el convención del repo).

2. **Copiar o alinear** la estructura con DataVerificationCleanner:
   - `app.py` con `create_app()`
   - `config.py` con clase `Config` y `load_dotenv()`
   - `requirements.txt` con versiones fijadas para Flask, cors, dotenv y lo que necesite el dominio
   - `.env.example` con todas las variables requeridas y comentarios breves

3. **En `create_app()`**:
   - `app.config.from_object(Config)`
   - `CORS(app)` si aplica
   - Inicializar recursos globales (p. ej. `db.init_pool(Config)` si hay PostgreSQL)
   - Registrar cada `Blueprint` con su `url_prefix` bajo `/api/v1/<dominio>`
   - Definir `GET /health` con `service` y `version` propios del microservicio
   - Registrar `@app.errorhandler` para 404, 405 y 500 devolviendo el envelope estándar

4. **Nombre del dominio en URL**: debe coincidir con la tabla de [api-contracts.md](../api-contracts.md) (p. ej. `/api/v1/verificacion`, `/api/v1/sentimiento`).

5. **Dashboard u otros backends**: si el servicio no es Flask (p. ej. otro stack en `DashboardBackend`), no es obligatorio seguir esta carpeta; estas instrucciones son para servicios **Flask** explícitos.

---

## 2. Añadir un endpoint

1. **Elegir el Blueprint** correcto o crear uno nuevo con `url_prefix="/api/v1/<dominio>"`.

2. **Documentar** encima de la función: método HTTP, ruta completa, body JSON o query params, y consumidores (scheduler, otro servicio, dashboard).

3. **Entrada**:
   - `request.get_json(silent=True)` para POST/PUT/PATCH; tratar `None` como body inválido si el endpoint exige JSON.
   - `request.args.get(..., type=int)` (u otros tipos) para query strings.

4. **Validación**: añadir o extender funciones en `routes/validators.py` que devuelvan `list[str]` de errores. Si hay errores, responder con `error("BODY_INVALIDO", ...)` o un código más específico y `400`.

5. **Lógica**: delegar en `services/` y `repositories/`; capturar excepciones de dominio y mapearlas a `error(codigo, mensaje, status=...)`.

6. **Salida**: usar helpers `ok(data)` / `error(...)` para mantener `{ ok, data, error }`.

7. **Contrato**: actualizar [api-contracts.md](../api-contracts.md) y [openapi.json](../openapi.json) con rutas, códigos de error y ejemplos de request/response.

---

## 3. Conectar PostgreSQL

1. Añadir variables `DB_*` y pool `DB_POOL_*` en `Config` (ver [config.py](../../sources/apis/DataVerificationCleanner/config.py)).

2. En `db.py`, implementar `init_pool`, `get_connection` y, si aplica, `close_pool` para shutdown limpio.

3. En `create_app()`, llamar a `init_pool(Config)` después de cargar la configuración.

4. En repositorios, métodos que acepten `conn=None` y obtengan conexión del pool solo cuando no se pase `conn` (patrón útil para transacciones multi-tabla).

5. Operaciones que deben ser **atómicas**: una sola `with get_connection() as conn:` y pasar `conn` a todos los repositorios involucrados.

---

## 4. Excepciones de dominio

1. Definir jerarquía en `services/exceptions.py` (o módulo equivalente) con nombres claros.

2. En **services**, lanzar esas excepciones; en **routes**, capturar y traducir a HTTP + `error.codigo` sin exponer trazas internas al cliente.

3. Errores de librerías (p. ej. `psycopg2.Error`): loguear y responder `500` con mensaje genérico salvo que tenga sentido un código de negocio documentado.

---

## 5. Checklist antes de considerar el cambio listo

- [ ] `GET /health` responde `200` con `ok`, `service`, `version` y `status`.
- [ ] Endpoints nuevos usan el envelope `{ ok, data, error }` como en [api-contracts.md](../api-contracts.md).
- [ ] Códigos `error.codigo` son `UPPER_SNAKE_CASE` y documentados donde el contrato lo requiera.
- [ ] Validación de entrada centralizada en `validators` cuando el body sea complejo.
- [ ] `.env.example` actualizado; ningún secreto en el código ni en commits.
- [ ] Logs útiles en errores y en pasos críticos del flujo.
- [ ] [openapi.json](../openapi.json) (y si aplica [api-contracts.md](../api-contracts.md)) al día con los cambios públicos.

---

## 6. Prueba manual rápida

Desde la raíz del servicio, con variables cargadas (o `.env`):

```bash
python app.py
```

Comprobar:

```http
GET http://localhost:<PORT>/health
```

Para un POST de ejemplo, usar el mismo host/puerto y el body documentado en el README del servicio o en [api-contracts.md](../api-contracts.md).

---

## Referencias

| Documento | Uso |
|-----------|-----|
| [guidelines.md](guidelines.md) | Normas de arquitectura y estilo |
| [api-contracts.md](../api-contracts.md) | Contratos entre servicios |
| [openapi.json](../openapi.json) | Especificación OpenAPI |
| [DataVerificationCleanner/README.md](../../sources/apis/DataVerificationCleanner/README.md) | Estructura y endpoints del ejemplo canónico |
