-- Tabla de trabajos OpenAI Batch API para ABSA (ABSAService).
-- Un archivo en estado 'predicted' puede tener como máximo un job pendiente
-- (estado_aplicacion = 'pendiente').

CREATE TABLE IF NOT EXISTS absa_openai_batches (
    id                 BIGSERIAL PRIMARY KEY,
    archivo_id         BIGINT      NOT NULL REFERENCES log_archivos(id),
    openai_batch_id    TEXT        NOT NULL UNIQUE,
    openai_input_file_id TEXT      NOT NULL,
    estado_openai      VARCHAR(40) NOT NULL DEFAULT 'validating',
    total_requests     INT         NOT NULL,
    estado_aplicacion  VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                       CHECK (estado_aplicacion IN ('pendiente', 'aplicado', 'fallido')),
    aplicado_en        TIMESTAMPTZ,
    error_mensaje      TEXT,
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_absa_openai_batches_archivo
    ON absa_openai_batches (archivo_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_absa_openai_un_archivo_pendiente
    ON absa_openai_batches (archivo_id)
    WHERE estado_aplicacion = 'pendiente';
