-- Migración: estados log_archivos.estado (es -> en)
-- Objetivo: corte limpio a estados en inglés:
--   received, validated, cleaned, predicted, topics_identified, completed, error
--
-- Nota: Ejecutar este script durante la ventana de migración, idealmente
-- junto con el cambio del CHECK/DEFAULT (ver guidelines/ddl_bd.sql).

BEGIN;

-- 1) Actualizar valores existentes (español -> inglés)
UPDATE log_archivos
SET estado = CASE estado
  WHEN 'recibido'   THEN 'received'
  WHEN 'validado'   THEN 'validated'
  WHEN 'limpio'     THEN 'cleaned'
  WHEN 'predicho'   THEN 'predicted'
  WHEN 'topicado'   THEN 'topics_identified'
  WHEN 'completado' THEN 'completed'
  WHEN 'error'      THEN 'error'
  ELSE estado
END;

-- 2) Verificación rápida (opcional, deja comentado si no se desea salida)
-- SELECT estado, COUNT(*) FROM log_archivos GROUP BY 1 ORDER BY 1;

COMMIT;

