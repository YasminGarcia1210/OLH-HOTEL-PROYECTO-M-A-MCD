#!/usr/bin/env python3
"""
Crea un usuario en la tabla `usuarios`.

Uso:
    python scripts/crear_usuario.py <username> <password> <nombre> [hotel_id]

    hotel_id  opcional — si se omite el usuario tiene acceso global a todos los hoteles.

Requiere que las variables de entorno DB_* estén configuradas (o un .env en la
raíz del proyecto).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor

from config import Config


def crear_usuario(username: str, password: str, nombre: str, hotel_id: int | None = None) -> None:
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        sslmode=Config.DB_SSLMODE,
    )
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO usuarios (username, password_hash, nombre, hotel_id)"
                " VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (username) DO NOTHING RETURNING id",
                (username, password_hash, nombre, hotel_id),
            )
            row = cur.fetchone()
            if row is None:
                print(f"El usuario '{username}' ya existe, no se realizó ningún cambio.")
            else:
                hotel_info = f"hotel_id={hotel_id}" if hotel_id else "acceso global"
                print(f"Usuario '{username}' creado con id={row['id']} ({hotel_info}).")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        print(f"Uso: python {sys.argv[0]} <username> <password> <nombre> [hotel_id]")
        sys.exit(1)

    _hotel_id = int(sys.argv[4]) if len(sys.argv) == 5 else None
    crear_usuario(sys.argv[1], sys.argv[2], sys.argv[3], _hotel_id)
