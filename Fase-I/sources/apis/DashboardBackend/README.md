# Dashboard Backend

API Flask que sirve al dashboard ejecutivo: **lecturas** de métricas pre-calculadas bajo `/api/v1/metricas` y el **Reviews Explorer** (`GET /metricas/reviews`). El cálculo batch (`POST /metricas/calcular`) está en [MetricProcessor](../MetricProcessor/); la lógica SQL de lectura se comparte vía el paquete [metricas_read](../../libs/metricas_read/).

## Arranque

```bash
cp .env.example .env
uv sync
# o: pip install -r requirements.txt
python app.py
```

Puerto por defecto: **5002** (`config.Config.PORT`).

## Tests

```bash
# Con uv y entorno sane: pytest en esta carpeta (requiere `metricas-read` instalado en editable).
uv run --group dev pytest

# Alternativa: desde MetricProcessor con PYTHONPATH (ver tests/conftest.py).
```

## Variables de entorno

Ver `.env.example`: `DB_*` alineadas con el resto de servicios que comparten la misma base PostgreSQL.
