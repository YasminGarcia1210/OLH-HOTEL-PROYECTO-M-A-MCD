"""Punto de entrada WSGI para Gunicorn en producción."""

from app import create_app

app = create_app()
