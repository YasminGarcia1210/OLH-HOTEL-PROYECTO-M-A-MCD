-- ================================================================
-- MODELO DE BASE DE DATOS – SISTEMA DE ANÁLISIS DE SENTIMIENTO
-- Hotel OLH · PostgreSQL
-- ================================================================


-- ================================================================
-- GRUPO 1: CATÁLOGOS
-- ================================================================

CREATE TABLE hoteles (
  id        SERIAL PRIMARY KEY,
  nombre    VARCHAR(150) NOT NULL,
  ciudad    VARCHAR(100),
  pais      VARCHAR(100),
  activo    BOOLEAN     DEFAULT TRUE,
  creado_en TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------

CREATE TABLE topicos (
  id            SERIAL PRIMARY KEY,
  slug          VARCHAR(60)  UNIQUE NOT NULL, -- 'limpieza', 'ruido', 'wifi'
  nombre        VARCHAR(120) NOT NULL,
  tipo          VARCHAR(20)  NOT NULL CHECK (tipo IN ('clave', 'adicional')),
  umbral_alerta SMALLINT     NOT NULL DEFAULT 65, -- score mínimo antes de alertar
  activo        BOOLEAN DEFAULT TRUE
);

-- ----------------------------------------------------------------

CREATE TABLE usuarios (
  id            SERIAL PRIMARY KEY,
  nombre        VARCHAR(120) NOT NULL,
  username      VARCHAR(100) UNIQUE NOT NULL,
  password_hash TEXT         NOT NULL,               -- bcrypt hash (work factor ≥ 12)
  hotel_id      INT          REFERENCES hoteles(id), -- NULL = acceso global
  activo        BOOLEAN      NOT NULL DEFAULT TRUE,
  creado_en     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ================================================================
-- GRUPO 2: PIPELINE AUDIT
-- Usado por todos los componentes para evitar reprocesamiento
-- y mantener trazabilidad del pipeline
-- ================================================================

CREATE TABLE log_archivos (
  id                    BIGSERIAL PRIMARY KEY,
  hotel_id              INT          REFERENCES hoteles(id),

  -- Archivo origen (Azure Blob: ruta dentro del contenedor; columna drive_id_* nombre histórico)
  nombre_archivo_origen VARCHAR(255) NOT NULL, -- 'reviews_olh_nov2025.csv'
  drive_id_origen       VARCHAR(200),          -- p. ej. 'entrada/reviews_olh_nov2025.csv'

  -- Archivo limpio generado en Azure Blob → nombre = prefijo + fecha procesamiento
  nombre_archivo_limpio VARCHAR(255),          -- 'clean_reviews_olh_2025-11-15.csv'
  drive_id_limpio       VARCHAR(200),          -- p. ej. 'limpios/reviews_olh_clean.csv'
  hash                  VARCHAR(64),            -- SHA-256 hex del contenido del blob de origen

  -- Estadísticas del proceso de limpieza
  total_registros       INT,
  registros_validos     INT,
  registros_descartados INT,

  -- Estado secuencial del pipeline
  estado                VARCHAR(30) NOT NULL DEFAULT 'received'
                        CHECK (estado IN (
                          'received',          -- archivo registrado en almacenamiento (Azure Blob)
                          'validated',         -- estructura y columnas correctas
                          'cleaned',           -- pipeline de limpieza ejecutado
                          'predicted',         -- sentimiento calculado para todas las reviews
                          'topics_identified', -- tópicos identificados
                          'completed',         -- métricas calculadas, listo para dashboard
                          'error'        -- fallo en alguna etapa
                        )),
  etapa_error           VARCHAR(50),    -- en qué etapa falló
  mensaje_error         TEXT,

  -- Timestamps por etapa
  fecha_recepcion       TIMESTAMPTZ DEFAULT NOW(),
  fecha_limpieza        TIMESTAMPTZ,
  fecha_prediccion      TIMESTAMPTZ,
  fecha_topicos         TIMESTAMPTZ,
  fecha_metricas        TIMESTAMPTZ
);

-- Sentiment Prediction consulta por nombre de archivo para evitar reprocesar
CREATE UNIQUE INDEX idx_log_nombre_origen
  ON log_archivos(nombre_archivo_origen);


-- ================================================================
-- GRUPO 3: DATOS NLP
-- ================================================================

-- Reviews limpias cargadas desde el CSV procesado
-- Input único: texto de la reseña (sin rating)
CREATE TABLE reviews (
  id           BIGSERIAL PRIMARY KEY,
  hotel_id     INT         NOT NULL REFERENCES hoteles(id),
  archivo_id   BIGINT      NOT NULL REFERENCES log_archivos(id),

  plataforma   VARCHAR(60),           -- 'booking', 'tripadvisor', 'google' (si viene en CSV)
  fecha_review DATE        NOT NULL,  -- fecha de la reseña original
  texto_limpio TEXT        NOT NULL,  -- output del pipeline de limpieza
  idioma       CHAR(5)     DEFAULT 'es',

  cargada_en   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reviews_hotel_fecha ON reviews(hotel_id, fecha_review);
CREATE INDEX idx_reviews_archivo     ON reviews(archivo_id);

-- ----------------------------------------------------------------
-- Predicciones de sentimiento (componente Sentiment Prediction)
-- Clase ganadora + confianza (max softmax) + vector softmax por clase (suma ≈ 1 salvo redondeo)
-- El score % del dashboard NO viene de aquí, lo calcula Metric Calculation
CREATE TABLE predicciones_sentimiento (
  id             BIGSERIAL PRIMARY KEY,
  review_id      BIGINT       NOT NULL REFERENCES reviews(id),

  sentimiento    VARCHAR(20)  NOT NULL
                 CHECK (sentimiento IN ('positivo', 'negativo', 'neutro')),
  confianza      NUMERIC(4,3) NOT NULL     -- probabilidad del modelo: 0.000 – 1.000
                 CHECK (confianza BETWEEN 0 AND 1),

  prob_negativo  NUMERIC(4,3)
                 CHECK (prob_negativo IS NULL OR prob_negativo BETWEEN 0 AND 1),
  prob_neutro    NUMERIC(4,3)
                 CHECK (prob_neutro IS NULL OR prob_neutro BETWEEN 0 AND 1),
  prob_positivo  NUMERIC(4,3)
                 CHECK (prob_positivo IS NULL OR prob_positivo BETWEEN 0 AND 1),

  modelo_version VARCHAR(50)  NOT NULL,    -- versión del modelo en el registry
  procesado_en   TIMESTAMPTZ  DEFAULT NOW(),

  UNIQUE(review_id)                        -- una sola predicción por review
);

CREATE INDEX idx_pred_review      ON predicciones_sentimiento(review_id);
CREATE INDEX idx_pred_sentimiento ON predicciones_sentimiento(sentimiento);

-- ----------------------------------------------------------------
-- Tópicos identificados por review (componente Topic Identification)
-- Una review puede pertenecer a múltiples tópicos
CREATE TABLE review_topicos (
  id             BIGSERIAL PRIMARY KEY,
  review_id      BIGINT       NOT NULL REFERENCES reviews(id),
  topico_id      INT          NOT NULL REFERENCES topicos(id),

  score_topico   NUMERIC(4,3),             -- confianza del modelo: 0.000 – 1.000
  fragmento      TEXT,                     -- fragmento del texto que activó el tópico
  sentimiento    VARCHAR(20)  CHECK (sentimiento IN ('positivo', 'negativo', 'neutro')),
                                           -- sentimiento específico del tópico en la review
                                           -- puede diferir del sentimiento global (reviews neutras
                                           -- pueden tener tópicos con sentimiento positivo/negativo)

  modelo_version VARCHAR(50)  NOT NULL,
  procesado_en   TIMESTAMPTZ  DEFAULT NOW(),

  UNIQUE(review_id, topico_id)             -- evita duplicados en reprocesamiento
);

CREATE INDEX idx_rt_review  ON review_topicos(review_id);
CREATE INDEX idx_rt_topico  ON review_topicos(topico_id);


-- ================================================================
-- GRUPO 4: MÉTRICAS PRE-CALCULADAS
-- Escritas por Metric Calculation · Solo lectura para el Dashboard
--
-- score (%) = (menciones_positivas / total) × 100
-- El dashboard nunca calcula: solo lee y grafica
-- ================================================================

-- Métricas globales por hotel y mes
-- → KPI "Sentimiento promedio", "Reviews analizadas", gráfico de línea principal
CREATE TABLE metricas_globales_mensual (
  id                      BIGSERIAL PRIMARY KEY,
  hotel_id                INT          NOT NULL REFERENCES hoteles(id),
  anio                    SMALLINT     NOT NULL,
  mes                     SMALLINT     NOT NULL CHECK (mes BETWEEN 1 AND 12),

  -- Conteos base
  total_reviews           INT          NOT NULL DEFAULT 0,
  reviews_positivas       INT          NOT NULL DEFAULT 0,
  reviews_negativas       INT          NOT NULL DEFAULT 0,
  reviews_neutras         INT          NOT NULL DEFAULT 0,

  -- Score derivado: (reviews_positivas / total_reviews) * 100
  score_promedio          NUMERIC(5,2) NOT NULL,
  cambio_pct_vs_anterior  NUMERIC(6,2),          -- ej: +4.2 o -1.5
  total_alertas           SMALLINT     NOT NULL DEFAULT 0,

  calculado_en            TIMESTAMPTZ  DEFAULT NOW(),

  UNIQUE(hotel_id, anio, mes)
);

CREATE INDEX idx_mgm_hotel_periodo
  ON metricas_globales_mensual(hotel_id, anio, mes);

-- ----------------------------------------------------------------
-- Métricas por tópico, hotel y mes
-- → Tarjetas de tópicos, Top 5 críticos, tabla de rendimiento,
--   tooltip del gráfico, modal de detalle
CREATE TABLE metricas_topico_mensual (
  id                      BIGSERIAL PRIMARY KEY,
  hotel_id                INT          NOT NULL REFERENCES hoteles(id),
  topico_id               INT          NOT NULL REFERENCES topicos(id),
  anio                    SMALLINT     NOT NULL,
  mes                     SMALLINT     NOT NULL CHECK (mes BETWEEN 1 AND 12),

  -- Conteos base
  total_menciones         INT          NOT NULL DEFAULT 0,
  menciones_positivas     INT          NOT NULL DEFAULT 0,
  menciones_negativas     INT          NOT NULL DEFAULT 0,
  menciones_neutras       INT          NOT NULL DEFAULT 0,

  -- Score derivado: (menciones_positivas / total_menciones) * 100
  score_promedio          NUMERIC(5,2) NOT NULL,
  cambio_pct_vs_anterior  NUMERIC(6,2),
  alerta                  BOOLEAN      NOT NULL DEFAULT FALSE,

  calculado_en            TIMESTAMPTZ  DEFAULT NOW(),

  UNIQUE(hotel_id, topico_id, anio, mes)
);

CREATE INDEX idx_mtm_hotel_periodo
  ON metricas_topico_mensual(hotel_id, anio, mes);
CREATE INDEX idx_mtm_alertas
  ON metricas_topico_mensual(hotel_id, alerta) WHERE alerta = TRUE;

-- ----------------------------------------------------------------
-- Alertas generadas por Metric Calculation
-- Cuando score_promedio de un tópico cae por debajo de umbral_alerta
CREATE TABLE alertas (
  id           BIGSERIAL PRIMARY KEY,
  hotel_id     INT          NOT NULL REFERENCES hoteles(id),
  topico_id    INT          NOT NULL REFERENCES topicos(id),
  anio         SMALLINT     NOT NULL,
  mes          SMALLINT     NOT NULL,

  score_actual NUMERIC(5,2),
  umbral_usado SMALLINT,
  mensaje      TEXT,

  resuelta     BOOLEAN      DEFAULT FALSE,
  resuelta_en  TIMESTAMPTZ,
  resuelta_por INT          REFERENCES usuarios(id),

  generada_en  TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX idx_alertas_hotel_activas
  ON alertas(hotel_id, resuelta) WHERE resuelta = FALSE;

-- ----------------------------------------------------------------
-- OpenAI Batch API (ABSAService): un job pendiente por archivo
-- Ver también guidelines/migracion_absa_openai_batches.sql
CREATE TABLE IF NOT EXISTS absa_openai_batches (
    id                     BIGSERIAL PRIMARY KEY,
    archivo_id             BIGINT      NOT NULL REFERENCES log_archivos(id),
    openai_batch_id        TEXT        NOT NULL UNIQUE,
    openai_input_file_id   TEXT        NOT NULL,
    estado_openai          VARCHAR(40) NOT NULL DEFAULT 'validating',
    total_requests         INT         NOT NULL,
    estado_aplicacion      VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                           CHECK (estado_aplicacion IN ('pendiente', 'aplicado', 'fallido')),
    aplicado_en            TIMESTAMPTZ,
    error_mensaje          TEXT,
    creado_en              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_absa_openai_batches_archivo
    ON absa_openai_batches (archivo_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_absa_openai_un_archivo_pendiente
    ON absa_openai_batches (archivo_id)
    WHERE estado_aplicacion = 'pendiente';