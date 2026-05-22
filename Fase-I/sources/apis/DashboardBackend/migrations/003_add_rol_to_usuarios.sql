-- Migración 003: agrega columna rol a la tabla usuarios.
-- DEFAULT 'viewer' para no romper filas existentes.
-- Actualizar manualmente los administradores:
--   UPDATE usuarios SET rol = 'admin' WHERE username = '<tu_admin>';

ALTER TABLE usuarios
    ADD COLUMN rol VARCHAR(20) NOT NULL DEFAULT 'viewer'
        CHECK (rol IN ('admin', 'viewer'));
