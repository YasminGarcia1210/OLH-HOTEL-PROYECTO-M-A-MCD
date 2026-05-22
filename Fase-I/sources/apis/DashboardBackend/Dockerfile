# Sin directiva `# syntax=docker/dockerfile:1`: en Podman (Windows) el frontend BuildKit
# puede tardar o parecer colgado al pull desde Docker Hub.
#
# Build desde la raíz del repo Tesis (carpeta que contiene `sources/`). Usá SIEMPRE
# --ignorefile con context.dockerignore: sin eso el contexto es TODO `sources/` (GB)
# y la terminal puede quedar en silencio mucho tiempo al enviar el tar a Podman Machine.
#
#   podman build `
#     --ignorefile sources/apis/DashboardBackend/context.dockerignore `
#     -f sources/apis/DashboardBackend/Dockerfile -t <tag> sources
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5002

COPY libs/metricas_read /app/libs/metricas_read
RUN pip install --no-cache-dir -e /app/libs/metricas_read

WORKDIR /app/api
COPY apis/DashboardBackend/requirements-docker.txt .
RUN pip uninstall -y jwt 2>/dev/null || true \
 && pip install --no-cache-dir -r requirements-docker.txt \
 && pip install --no-cache-dir --force-reinstall "PyJWT==2.9.0" "flask-jwt-extended==4.7.1" \
 && python -c "import importlib.metadata as m; print('PyJWT', m.version('PyJWT'), 'flask-jwt-extended', m.version('flask-jwt-extended'))" \
 && python -c "import jwt, flask_jwt_extended; print('jwt module:', jwt.__file__)"

COPY apis/DashboardBackend .

# Falla el build si el arranque WSGI importa mal (JWT, rutas, etc.).
RUN python -c "from wsgi import app; print('wsgi boot ok:', app.name)"

EXPOSE 5002

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 300 --access-logfile - --error-logfile - wsgi:app"]
