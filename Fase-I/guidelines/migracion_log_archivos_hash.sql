-- Migración: columna log_archivos.hash (SHA-256 hex del blob de origen descargado)
-- Objetivo: trazabilidad de integridad del archivo procesado desde Azure Blob.
-- Valores NULL en filas históricas hasta reprocesamiento manual si aplica.

BEGIN;

ALTER TABLE log_archivos
  ADD COLUMN IF NOT EXISTS hash VARCHAR(64);

COMMIT;
