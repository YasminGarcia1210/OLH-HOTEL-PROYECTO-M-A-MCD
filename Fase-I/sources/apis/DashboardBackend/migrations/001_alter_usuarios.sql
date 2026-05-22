-- Migración 001 (alter): actualiza la tabla usuarios existente al nuevo esquema de auth.
-- Elimina email y rol; agrega username y password_hash.
--
-- Si la tabla tiene filas existentes, agregar primero las columnas como nullable,
-- poblarlas y luego aplicar NOT NULL (ver pasos comentados al final).

ALTER TABLE usuarios
    DROP COLUMN  email,
    DROP COLUMN  rol,
    ADD  COLUMN  username      VARCHAR(100) UNIQUE NOT NULL,
    ADD  COLUMN  password_hash TEXT         NOT NULL;
