-- =============================================================================
--  YakuAlerta — inicialización de la base de datos (PostgreSQL 16 + PostGIS)
--  Ejecutado automáticamente por el contenedor de Postgres en el primer arranque.
--  Modelo físico 3NF (14 tablas) del documento de modelamiento de BD.
-- =============================================================================
-- PostGIS es opcional (el MVP usa lat/long decimales, no geometrías).
-- Si la extensión no está disponible, se continúa sin ella.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS postgis;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'PostGIS no disponible; se continua sin el (no es requerido por el MVP).';
END $$;

-- ---------------------------------------------------------------------------
--  0. TIPOS ENUMERADOS (dominios controlados del negocio)
-- ---------------------------------------------------------------------------
-- Roles: los seis operativos más los exigidos por las bases del Desafío 2
-- (autoridad local, DRVCS y contacto comunitario para la población usuaria).
CREATE TYPE rol_usuario      AS ENUM ('OPERADOR','DIRECTIVO_JASS','ATM','DESA','SALUD','ADMIN',
                                      'AUTORIDAD_LOCAL','DRVCS','POBLACION');
CREATE TYPE nivel_riesgo     AS ENUM ('VERDE','AMARILLO','ROJO');
CREATE TYPE metodo_lectura   AS ENUM ('CAMARA_DPD','MANUAL');
CREATE TYPE estado_sync      AS ENUM ('PENDIENTE','ENVIADO_SMS','SINCRONIZADO');
CREATE TYPE estado_alerta    AS ENUM ('ACTIVA','EN_PROCESO','CERRADA');
CREATE TYPE canal_notif      AS ENUM ('SMS','WHATSAPP','APP');
CREATE TYPE estado_notif     AS ENUM ('ENVIADO','ENTREGADO','FALLIDO');
CREATE TYPE dictamen_lab     AS ENUM ('CONFORME','NO_CONFORME');
CREATE TYPE estado_qr        AS ENUM ('PENDIENTE','ESCANEADO','APROBADO','RECHAZADO','CONSUMIDA','EXPIRADO');

-- ---------------------------------------------------------------------------
--  1. UBIGEO
-- ---------------------------------------------------------------------------
CREATE TABLE ubigeo (
    ubigeo_id        SERIAL       PRIMARY KEY,
    codigo_ubigeo    CHAR(6)      NOT NULL UNIQUE,
    departamento     VARCHAR(60)  NOT NULL DEFAULT 'HUANCAVELICA',
    provincia        VARCHAR(60)  NOT NULL,
    distrito         VARCHAR(60)  NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
--  2. COMUNIDAD
-- ---------------------------------------------------------------------------
CREATE TABLE comunidad (
    comunidad_id     SERIAL       PRIMARY KEY,
    ubigeo_id        INT          NOT NULL,
    nombre           VARCHAR(120) NOT NULL,
    latitud          DECIMAL(9,6),
    longitud         DECIMAL(9,6),
    poblacion_servida INT         CHECK (poblacion_servida >= 0),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_comunidad_ubigeo
        FOREIGN KEY (ubigeo_id) REFERENCES ubigeo(ubigeo_id) ON DELETE RESTRICT,
    CONSTRAINT uq_comunidad UNIQUE (ubigeo_id, nombre)
);

-- ---------------------------------------------------------------------------
--  3. RESERVORIO
-- ---------------------------------------------------------------------------
CREATE TABLE reservorio (
    reservorio_id    SERIAL       PRIMARY KEY,
    comunidad_id     INT          NOT NULL,
    codigo           VARCHAR(30)  NOT NULL UNIQUE,
    volumen_m3       DECIMAL(8,2) NOT NULL CHECK (volumen_m3 > 0),
    tipo_sistema     VARCHAR(60),
    estado_infra     VARCHAR(60),
    umbral_silencio_dias SMALLINT NOT NULL DEFAULT 7 CHECK (umbral_silencio_dias > 0),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_reservorio_comunidad
        FOREIGN KEY (comunidad_id) REFERENCES comunidad(comunidad_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
--  4. USUARIO
-- ---------------------------------------------------------------------------
CREATE TABLE usuario (
    usuario_id       SERIAL       PRIMARY KEY,
    nombres          VARCHAR(120) NOT NULL,
    dni              CHAR(8)      UNIQUE,                  -- identificador de acceso desde la app
    telefono         VARCHAR(15)  NOT NULL UNIQUE,
    clave_hash       VARCHAR(255) NOT NULL,
    rol              rol_usuario  NOT NULL,
    entidad          VARCHAR(120),
    ubigeo_id        INT,                                   -- ámbito distrital (NULL = regional)
    comunidad_id     INT,                                   -- ámbito comunal  (NULL = todo el distrito)
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_usuario_ubigeo
        FOREIGN KEY (ubigeo_id) REFERENCES ubigeo(ubigeo_id) ON DELETE SET NULL,
    CONSTRAINT fk_usuario_comunidad
        FOREIGN KEY (comunidad_id) REFERENCES comunidad(comunidad_id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------------------
--  5. ASIGNACION_OPERADOR (N:M usuario-operador ↔ reservorio)
-- ---------------------------------------------------------------------------
CREATE TABLE asignacion_operador (
    asignacion_id    SERIAL       PRIMARY KEY,
    usuario_id       INT          NOT NULL,
    reservorio_id    INT          NOT NULL,
    fecha_inicio     DATE         NOT NULL DEFAULT CURRENT_DATE,
    fecha_fin        DATE,
    vigente          BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_asig_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id) ON DELETE CASCADE,
    CONSTRAINT fk_asig_reservorio
        FOREIGN KEY (reservorio_id) REFERENCES reservorio(reservorio_id) ON DELETE CASCADE,
    CONSTRAINT uq_asig UNIQUE (usuario_id, reservorio_id, fecha_inicio),
    CONSTRAINT chk_fechas CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)
);

-- ---------------------------------------------------------------------------
--  6. PARAMETRO_NORMATIVO (umbrales configurables — D.S. 031-2010-SA)
-- ---------------------------------------------------------------------------
CREATE TABLE parametro_normativo (
    parametro_id     SERIAL       PRIMARY KEY,
    parametro        VARCHAR(40)  NOT NULL UNIQUE,
    unidad           VARCHAR(15)  NOT NULL,
    umbral_amarillo  DECIMAL(8,3),
    umbral_rojo      DECIMAL(8,3),
    norma_referencia VARCHAR(80)  NOT NULL DEFAULT 'D.S. 031-2010-SA',
    vigente          BOOLEAN      NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------------
--  7. MEDICION (núcleo del sistema)
-- ---------------------------------------------------------------------------
CREATE TABLE medicion (
    medicion_id      BIGSERIAL    PRIMARY KEY,
    uuid_registro    UUID         NOT NULL UNIQUE,
    reservorio_id    INT          NOT NULL,
    usuario_id       INT          NOT NULL,
    fecha_hora       TIMESTAMPTZ  NOT NULL,
    cloro_mg_l       DECIMAL(5,2) CHECK (cloro_mg_l >= 0 AND cloro_mg_l <= 20),
    turbidez_unt     DECIMAL(6,2) CHECK (turbidez_unt >= 0),
    metodo_cloro     metodo_lectura NOT NULL DEFAULT 'MANUAL',
    observaciones    TEXT,
    nivel_riesgo     nivel_riesgo NOT NULL,
    estado_sync      estado_sync  NOT NULL DEFAULT 'PENDIENTE',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_medicion_reservorio
        FOREIGN KEY (reservorio_id) REFERENCES reservorio(reservorio_id) ON DELETE RESTRICT,
    CONSTRAINT fk_medicion_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------------
--  8. EVIDENCIA_FOTO
-- ---------------------------------------------------------------------------
CREATE TABLE evidencia_foto (
    evidencia_id     BIGSERIAL    PRIMARY KEY,
    medicion_id      BIGINT       NOT NULL,
    ruta_archivo     VARCHAR(255) NOT NULL,
    latitud          DECIMAL(9,6),
    longitud         DECIMAL(9,6),
    fecha_hora       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_evidencia_medicion
        FOREIGN KEY (medicion_id) REFERENCES medicion(medicion_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
--  9. RECOMENDACION_DOSIS (1:1 con medición)
-- ---------------------------------------------------------------------------
CREATE TABLE recomendacion_dosis (
    recomendacion_id BIGSERIAL    PRIMARY KEY,
    medicion_id      BIGINT       NOT NULL UNIQUE,
    gramos_hipoclorito DECIMAL(8,2) CHECK (gramos_hipoclorito >= 0),
    concentracion_insumo DECIMAL(5,2),
    plazo_remedicion_hrs SMALLINT CHECK (plazo_remedicion_hrs > 0),
    protocolo        TEXT,
    CONSTRAINT fk_reco_medicion
        FOREIGN KEY (medicion_id) REFERENCES medicion(medicion_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
--  10. ALERTA (1:1 con la medición que la origina)
-- ---------------------------------------------------------------------------
CREATE TABLE alerta (
    alerta_id        BIGSERIAL    PRIMARY KEY,
    medicion_id      BIGINT       NOT NULL UNIQUE,
    nivel            nivel_riesgo NOT NULL,
    estado           estado_alerta NOT NULL DEFAULT 'ACTIVA',
    fecha_generacion TIMESTAMPTZ  NOT NULL DEFAULT now(),
    fecha_cierre     TIMESTAMPTZ,
    medicion_cierre_id BIGINT,
    resultado_cierre VARCHAR(120),
    usuario_cierre_id INT,
    CONSTRAINT fk_alerta_medicion
        FOREIGN KEY (medicion_id) REFERENCES medicion(medicion_id) ON DELETE CASCADE,
    CONSTRAINT fk_alerta_medicion_cierre
        FOREIGN KEY (medicion_cierre_id) REFERENCES medicion(medicion_id) ON DELETE SET NULL,
    CONSTRAINT fk_alerta_usuario_cierre
        FOREIGN KEY (usuario_cierre_id) REFERENCES usuario(usuario_id) ON DELETE SET NULL,
    CONSTRAINT chk_nivel_alerta CHECK (nivel IN ('AMARILLO','ROJO')),
    CONSTRAINT chk_cierre CHECK (
        (estado = 'CERRADA' AND fecha_cierre IS NOT NULL)
        OR (estado <> 'CERRADA')
    )
);

-- ---------------------------------------------------------------------------
--  11. NOTIFICACION
-- ---------------------------------------------------------------------------
CREATE TABLE notificacion (
    notificacion_id  BIGSERIAL    PRIMARY KEY,
    alerta_id        BIGINT       NOT NULL,
    usuario_id       INT          NOT NULL,
    canal            canal_notif  NOT NULL,
    mensaje          TEXT         NOT NULL,
    estado_entrega   estado_notif NOT NULL DEFAULT 'ENVIADO',
    fecha_hora       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_notif_alerta
        FOREIGN KEY (alerta_id) REFERENCES alerta(alerta_id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------------
--  12. RESULTADO_LABORATORIO
-- ---------------------------------------------------------------------------
CREATE TABLE resultado_laboratorio (
    resultado_id     BIGSERIAL    PRIMARY KEY,
    reservorio_id    INT          NOT NULL,
    usuario_id       INT          NOT NULL,
    parametro        VARCHAR(60)  NOT NULL,
    valor            DECIMAL(12,4),
    unidad           VARCHAR(20),
    dictamen         dictamen_lab NOT NULL,
    fecha_muestreo   DATE         NOT NULL,
    laboratorio      VARCHAR(120),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_lab_reservorio
        FOREIGN KEY (reservorio_id) REFERENCES reservorio(reservorio_id) ON DELETE CASCADE,
    CONSTRAINT fk_lab_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------------
--  13. REPORTE
-- ---------------------------------------------------------------------------
CREATE TABLE reporte (
    reporte_id       BIGSERIAL    PRIMARY KEY,
    ubigeo_id        INT          NOT NULL,
    usuario_id       INT          NOT NULL,
    periodo          VARCHAR(7)   NOT NULL,
    formato          VARCHAR(5)   NOT NULL DEFAULT 'PDF' CHECK (formato IN ('PDF','XLSX')),
    ruta_archivo     VARCHAR(255),
    fecha_generacion TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_reporte_ubigeo
        FOREIGN KEY (ubigeo_id) REFERENCES ubigeo(ubigeo_id) ON DELETE RESTRICT,
    CONSTRAINT fk_reporte_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------------
--  15. SESION_QR  (vinculación efímera web-movil, patrón WhatsApp/Discord Web)
-- ---------------------------------------------------------------------------
CREATE TABLE sesion_qr (
    sesion_qr_id     BIGSERIAL    PRIMARY KEY,
    token            VARCHAR(64)  NOT NULL UNIQUE,      -- secreto público del QR
    client_hash      VARCHAR(64)  NOT NULL,             -- SHA-256 del secreto del navegador
    estado           estado_qr    NOT NULL DEFAULT 'PENDIENTE',
    usuario_id       INT,                               -- quien escanea y autoriza
    creado_en        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expira_en        TIMESTAMPTZ  NOT NULL,
    escaneado_en     TIMESTAMPTZ,
    resuelto_en      TIMESTAMPTZ,
    ip_origen        VARCHAR(45),
    user_agent       VARCHAR(255),
    CONSTRAINT fk_sesionqr_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id) ON DELETE CASCADE
);
CREATE INDEX idx_sesionqr_token  ON sesion_qr(token);
CREATE INDEX idx_sesionqr_estado ON sesion_qr(estado);

-- ---------------------------------------------------------------------------
--  16. RECUPERACION_CLAVE  (código de un solo uso enviado por SMS)
-- ---------------------------------------------------------------------------
CREATE TABLE recuperacion_clave (
    recuperacion_id  BIGSERIAL    PRIMARY KEY,
    usuario_id       INT          NOT NULL,
    codigo_hash      VARCHAR(255) NOT NULL,      -- el código se guarda cifrado
    expira_en        TIMESTAMPTZ  NOT NULL,
    intentos         INT          NOT NULL DEFAULT 0,
    usado            BOOLEAN      NOT NULL DEFAULT FALSE,
    creado_en        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    ip_origen        VARCHAR(45),
    CONSTRAINT fk_recuperacion_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id) ON DELETE CASCADE
);
CREATE INDEX idx_recuperacion_usuario ON recuperacion_clave(usuario_id);

-- ---------------------------------------------------------------------------
--  14. AUDITORIA
-- ---------------------------------------------------------------------------
CREATE TABLE auditoria (
    auditoria_id     BIGSERIAL    PRIMARY KEY,
    usuario_id       INT,
    accion           VARCHAR(60)  NOT NULL,
    entidad_afectada VARCHAR(60),
    registro_id      VARCHAR(60),
    detalle          TEXT,
    ip_origen        VARCHAR(45),
    fecha_hora       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_auditoria_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id) ON DELETE SET NULL
);

-- =============================================================================
--  ÍNDICES
-- =============================================================================
CREATE INDEX idx_comunidad_ubigeo      ON comunidad(ubigeo_id);
CREATE INDEX idx_reservorio_comunidad  ON reservorio(comunidad_id);
CREATE INDEX idx_asig_usuario          ON asignacion_operador(usuario_id);
CREATE INDEX idx_asig_reservorio       ON asignacion_operador(reservorio_id);
CREATE INDEX idx_medicion_reservorio   ON medicion(reservorio_id);
CREATE INDEX idx_medicion_usuario      ON medicion(usuario_id);
CREATE INDEX idx_medicion_fecha        ON medicion(fecha_hora);
CREATE INDEX idx_medicion_nivel        ON medicion(nivel_riesgo);
CREATE INDEX idx_medicion_sync         ON medicion(estado_sync);
CREATE INDEX idx_evidencia_medicion    ON evidencia_foto(medicion_id);
CREATE INDEX idx_alerta_estado         ON alerta(estado);
CREATE INDEX idx_notif_alerta          ON notificacion(alerta_id);
CREATE INDEX idx_notif_usuario         ON notificacion(usuario_id);
CREATE INDEX idx_lab_reservorio        ON resultado_laboratorio(reservorio_id);
CREATE INDEX idx_reporte_ubigeo        ON reporte(ubigeo_id);
CREATE INDEX idx_auditoria_usuario     ON auditoria(usuario_id);
CREATE INDEX idx_auditoria_fecha       ON auditoria(fecha_hora);

-- =============================================================================
--  SEED de catálogos normativos (umbrales del D.S. N.° 031-2010-SA — RNF-07)
--  Los datos demo (usuarios, comunidades) se cargan desde app/seed.py (bcrypt).
-- =============================================================================
INSERT INTO parametro_normativo (parametro, unidad, umbral_amarillo, umbral_rojo, norma_referencia) VALUES
    ('cloro_residual', 'mg/L', 0.500, 0.300, 'D.S. 031-2010-SA'),  -- >=0.5 verde; 0.30-0.49 amarillo; <0.30 rojo
    ('turbidez',       'UNT',  5.000, 5.000, 'D.S. 031-2010-SA')   -- <=5 ok; >5 rojo
ON CONFLICT (parametro) DO NOTHING;
