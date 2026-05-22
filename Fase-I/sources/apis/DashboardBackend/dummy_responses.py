"""Payloads de ejemplo alineados con los esquemas de openapi.json (tag Dashboard)."""


def kpis():
    return {
        "sentimiento_promedio": {
            "score": 68.40,
            "cambio_pct": 2.1,
            "tendencia": "up",
        },
        "reviews_analizadas": 1432,
        "topicos_con_alerta": 2,
    }


def sentimiento_mensual():
    return [
        {
            "anio": 2025,
            "mes": m,
            "score_promedio": 65.0 + (m % 5),
            "total_reviews": 100 + m * 10,
        }
        for m in range(7, 13)
    ]


def topicos():
    return [
        {
            "topico_id": 7,
            "slug": "ruido",
            "nombre": "Ruido",
            "tipo": "adicional",
            "score_promedio": 52.30,
            "cambio_pct_vs_anterior": -5.2,
            "total_menciones": 310,
            "alerta": True,
            "tendencia": "down",
        },
        {
            "topico_id": 3,
            "slug": "limpieza",
            "nombre": "Limpieza",
            "tipo": "clave",
            "score_promedio": 78.50,
            "cambio_pct_vs_anterior": 1.3,
            "total_menciones": 420,
            "alerta": False,
            "tendencia": "stable",
        },
    ]


def top5():
    slugs = [
        ("ruido", "Ruido", 52.30, True),
        ("wifi", "Wi‑Fi", 55.10, True),
        ("desayuno", "Desayuno", 58.00, False),
        ("recepcion", "Recepción", 61.20, False),
        ("habitacion", "Habitación", 63.80, False),
    ]
    return [
        {
            "posicion": i + 1,
            "slug": s[0],
            "nombre": s[1],
            "score_promedio": s[2],
            "alerta": s[3],
        }
        for i, s in enumerate(slugs)
    ]


def topico_detalle(slug: str):
    return {
        "slug": slug,
        "nombre": slug.replace("-", " ").title(),
        "score_promedio": 52.30,
        "cambio_pct_vs_anterior": -5.2,
        "alerta": True,
        "umbral_alerta": 65,
        "menciones": {
            "total": 310,
            "positivas": 82,
            "negativas": 193,
            "neutras": 35,
        },
        "fragmentos_destacados": [
            {
                "sentimiento": "negativo",
                "fragmento": "El ruido de la calle no nos dejó descansar.",
                "confianza": 0.951,
            },
            {
                "sentimiento": "negativo",
                "fragmento": "Se escuchaba todo desde el pasillo.",
                "confianza": 0.88,
            },
        ],
    }


def alertas():
    return [
        {
            "alerta_id": 5,
            "topico_slug": "ruido",
            "topico_nombre": "Ruido",
            "anio": 2025,
            "mes": 11,
            "score_actual": 52.30,
            "umbral_usado": 65,
            "mensaje": "Score de Ruido cayó a 52.3%, por debajo del umbral de 65%.",
            "generada_en": "2025-11-15T10:05:00Z",
        }
    ]


def reviews_list():
    item = {
        "review_id": 5001,
        "hotel_id": 1,
        "fecha_review": "2023-10-12",
        "texto_limpio": "Our stay was absolutely magnificent from the moment we arrived.",
        "plataforma": "Booking.com",
        "idioma": "en",
        "titulo": "Excellent Stay in the Master Suite",
        "prediccion": {
            "sentimiento": "positivo",
            "confianza": 0.923,
            "modelo_version": "sentiment-beto-v2.1",
        },
        "topicos": [
            {
                "topico_id": 1,
                "slug": "limpieza",
                "nombre": "Limpieza",
                "score_topico": 0.912,
                "sentimiento": "positivo",
                "fragmento": "La habitación estaba impecable cada día.",
            }
        ],
    }
    return {
        "items": [item],
        "paginacion": {
            "page": 1,
            "page_size": 20,
            "total": 1,
            "total_pages": 1,
        },
    }
