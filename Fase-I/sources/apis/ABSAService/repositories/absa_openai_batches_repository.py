"""
Persistencia de trabajos OpenAI Batch para ABSA.
"""

import logging
from typing import Any

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class AbsaOpenaiBatchesRepository:

    def insertar(
        self,
        conn,
        archivo_id: int,
        openai_batch_id: str,
        openai_input_file_id: str,
        estado_openai: str,
        total_requests: int,
    ) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO absa_openai_batches (
                    archivo_id, openai_batch_id, openai_input_file_id,
                    estado_openai, total_requests, estado_aplicacion
                )
                VALUES (%s, %s, %s, %s, %s, 'pendiente')
                RETURNING id
                """,
                (archivo_id, openai_batch_id, openai_input_file_id, estado_openai, total_requests),
            )
            row = cur.fetchone()
            new_id = row[0] if row else 0
        logger.info(
            "absa_openai_batches insertado id=%s archivo_id=%s batch=%s",
            new_id, archivo_id, openai_batch_id,
        )
        return new_id

    def buscar_pendiente_por_archivo(self, conn, archivo_id: int) -> dict[str, Any] | None:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, archivo_id, openai_batch_id, openai_input_file_id,
                       estado_openai, total_requests, estado_aplicacion,
                       aplicado_en, error_mensaje, creado_en
                FROM   absa_openai_batches
                WHERE  archivo_id = %s AND estado_aplicacion = 'pendiente'
                LIMIT  1
                """,
                (archivo_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def listar_pendientes(self, conn) -> list[dict[str, Any]]:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, archivo_id, openai_batch_id, openai_input_file_id,
                       estado_openai, total_requests, estado_aplicacion,
                       aplicado_en, error_mensaje, creado_en
                FROM   absa_openai_batches
                WHERE  estado_aplicacion = 'pendiente'
                ORDER BY creado_en ASC
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def buscar_por_openai_batch_id(self, conn, openai_batch_id: str) -> dict[str, Any] | None:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, archivo_id, openai_batch_id, openai_input_file_id,
                       estado_openai, total_requests, estado_aplicacion,
                       aplicado_en, error_mensaje, creado_en
                FROM   absa_openai_batches
                WHERE  openai_batch_id = %s
                LIMIT  1
                """,
                (openai_batch_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def actualizar_estado_openai(self, conn, openai_batch_id: str, estado_openai: str) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE absa_openai_batches
                SET    estado_openai = %s
                WHERE  openai_batch_id = %s AND estado_aplicacion = 'pendiente'
                """,
                (estado_openai, openai_batch_id),
            )

    def marcar_aplicado(self, conn, openai_batch_id: str) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE absa_openai_batches
                SET    estado_aplicacion = 'aplicado',
                       aplicado_en = NOW()
                WHERE  openai_batch_id = %s AND estado_aplicacion = 'pendiente'
                """,
                (openai_batch_id,),
            )

    def marcar_fallido(self, conn, openai_batch_id: str, mensaje: str) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE absa_openai_batches
                SET    estado_aplicacion = 'fallido',
                       error_mensaje = %s,
                       aplicado_en = NOW()
                WHERE  openai_batch_id = %s AND estado_aplicacion = 'pendiente'
                """,
                (mensaje[:2000], openai_batch_id),
            )
