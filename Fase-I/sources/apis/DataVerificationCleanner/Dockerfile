# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    PORT=5001

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download es_core_news_sm

# Reduce latencia del primer request (tokenizador BERT español).
RUN mkdir -p "$HF_HOME" \
    && python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('dccuchile/bert-base-spanish-wwm-cased')"

COPY . .

EXPOSE 5001

# Un worker por réplica evita duplicar modelos en memoria; timeout alto para CSV grandes.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 900 --access-logfile - --error-logfile - wsgi:app"]
