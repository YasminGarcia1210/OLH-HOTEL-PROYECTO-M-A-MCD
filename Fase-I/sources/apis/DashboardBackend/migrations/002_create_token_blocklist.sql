-- Migración 002: tabla de tokens revocados (blocklist JWT)
-- Ejecutar después de 001_create_usuarios.sql.

CREATE TABLE IF NOT EXISTS token_blocklist (
    id         SERIAL PRIMARY KEY,
    jti        VARCHAR(36) UNIQUE NOT NULL,   -- JWT ID (claim "jti")
    tipo       VARCHAR(10) NOT NULL,           -- 'access' | 'refresh'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_blocklist_jti ON token_blocklist (jti);

COMMENT ON TABLE  token_blocklist      IS 'JWTs revocados por logout o administración';
COMMENT ON COLUMN token_blocklist.jti  IS 'Claim jti del JWT — UUID generado por Flask-JWT-Extended';
COMMENT ON COLUMN token_blocklist.tipo IS 'Tipo de token: access o refresh';
