-- Migración 001: tabla de usuarios para autenticación JWT
-- Reemplaza la definición original del DDL: elimina email y rol,
-- agrega username (login) y password_hash (bcrypt).
-- Ejecutar una sola vez contra la base de datos del proyecto.

CREATE TABLE IF NOT EXISTS usuarios (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(120) NOT NULL,
    username      VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT         NOT NULL,            -- bcrypt hash (work factor ≥ 12)
    hotel_id      INT          REFERENCES hoteles(id), -- NULL = acceso global
    activo        BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  usuarios              IS 'Usuarios con acceso al Dashboard Backend';
COMMENT ON COLUMN usuarios.hotel_id     IS 'Hotel al que pertenece el usuario; NULL = acceso a todos los hoteles';
COMMENT ON COLUMN usuarios.password_hash IS 'Hash bcrypt de la contraseña (work factor ≥ 12)';
