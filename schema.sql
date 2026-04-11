-- ============================================================
-- CINEMAX — Schema PostgreSQL completo
-- Persistencia de cuentas, tiquetes, asientos y tarjetas
-- Cada cuenta tiene su propia información aislada
-- ============================================================

-- ── Extensión para UUIDs ───────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ══════════════════════════════════════════════════════════
-- 1. USUARIOS / CUENTAS
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS usuarios (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(200) UNIQUE NOT NULL,
    contrasena  VARCHAR(255) NOT NULL,       -- hash bcrypt
    nombre      VARCHAR(150) NOT NULL,
    rol         VARCHAR(60)  NOT NULL DEFAULT 'Usuario',
    color       VARCHAR(20)  NOT NULL DEFAULT '#00d4ff',  -- color avatar
    iniciales   VARCHAR(4)   NOT NULL DEFAULT '??',
    creado_en   TIMESTAMP    NOT NULL DEFAULT NOW(),
    activo      BOOLEAN      NOT NULL DEFAULT TRUE
);

-- Índice para búsqueda rápida por email en login
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);

-- ══════════════════════════════════════════════════════════
-- 2. PELÍCULAS  (catálogo)
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS peliculas (
    id          SERIAL PRIMARY KEY,
    titulo      VARCHAR(200) NOT NULL,
    genero      VARCHAR(80),
    duracion    INTEGER,                     -- minutos
    clasificacion VARCHAR(10),               -- ATP, +13, +18…
    idioma      VARCHAR(80),
    director    VARCHAR(150),
    reparto     TEXT,
    sinopsis    TEXT,
    poster_url  TEXT,
    rating      NUMERIC(3,1),
    tags        VARCHAR(300),
    activa      BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ══════════════════════════════════════════════════════════
-- 3. FUNCIONES (showtimes)
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS funciones (
    id          SERIAL PRIMARY KEY,
    pelicula_id INTEGER NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    sala        VARCHAR(80)  NOT NULL DEFAULT 'Sala 1',
    ciudad      VARCHAR(100),
    sede        VARCHAR(150),                -- nombre del multicines
    fecha       DATE         NOT NULL,
    hora        TIME         NOT NULL,
    precio_normal  NUMERIC(10,0) NOT NULL DEFAULT 18000,
    precio_vip     NUMERIC(10,0) NOT NULL DEFAULT 28000,
    precio_ultra   NUMERIC(10,0) NOT NULL DEFAULT 38000,
    estado      VARCHAR(20)  NOT NULL DEFAULT 'disponible'
                    CHECK (estado IN ('disponible','cancelada','agotada')),
    creado_en   TIMESTAMP    NOT NULL DEFAULT NOW(),
    -- Anti-traslape: misma sala, sede, fecha y hora
    UNIQUE (sala, sede, fecha, hora)
);

CREATE INDEX IF NOT EXISTS idx_funciones_pelicula ON funciones(pelicula_id);
CREATE INDEX IF NOT EXISTS idx_funciones_fecha    ON funciones(fecha);

-- ══════════════════════════════════════════════════════════
-- 4. ASIENTOS
-- Estructura fija por sala; se precarga una vez
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS asientos (
    id      SERIAL PRIMARY KEY,
    sala    VARCHAR(80) NOT NULL,
    sede    VARCHAR(150),
    zona    VARCHAR(20) NOT NULL CHECK (zona IN ('normal','vip','ultra')),
    fila    CHAR(1)     NOT NULL,
    numero  INTEGER     NOT NULL,
    activo  BOOLEAN     NOT NULL DEFAULT TRUE,
    UNIQUE (sala, sede, zona, fila, numero)
);

-- ══════════════════════════════════════════════════════════
-- 5. TIQUETES  (una fila por compra, puede incluir N asientos)
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS tiquetes (
    id              SERIAL PRIMARY KEY,
    codigo_qr       VARCHAR(60) UNIQUE NOT NULL,  -- ej: CX-LK3M9P-ABC123
    usuario_id      INTEGER     NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    funcion_id      INTEGER     NOT NULL REFERENCES funciones(id) ON DELETE RESTRICT,
    metodo_pago     VARCHAR(30) NOT NULL DEFAULT 'efectivo'
                        CHECK (metodo_pago IN ('card','nequi','daviplata','bancolombia','efectivo')),
    total           NUMERIC(12,0) NOT NULL,
    combo_detalle   TEXT,                          -- descripción de combos
    estado          VARCHAR(20) NOT NULL DEFAULT 'activo'
                        CHECK (estado IN ('activo','usado','cancelado')),
    comprado_en     TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tiquetes_usuario  ON tiquetes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_tiquetes_funcion  ON tiquetes(funcion_id);
CREATE INDEX IF NOT EXISTS idx_tiquetes_codigo   ON tiquetes(codigo_qr);

-- ══════════════════════════════════════════════════════════
-- 6. DETALLE DE TIQUETE  (asientos incluidos en cada compra)
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS detalle_tiquete (
    id          SERIAL PRIMARY KEY,
    tiquete_id  INTEGER NOT NULL REFERENCES tiquetes(id) ON DELETE CASCADE,
    asiento_id  INTEGER NOT NULL REFERENCES asientos(id) ON DELETE RESTRICT,
    zona        VARCHAR(20) NOT NULL,
    fila        CHAR(1)     NOT NULL,
    numero      INTEGER     NOT NULL,
    precio      NUMERIC(10,0) NOT NULL,
    -- REGLA CRÍTICA: un asiento no puede venderse dos veces en la misma función
    -- (la restricción real se hace a nivel de funcion_asientos_ocupados)
    UNIQUE (tiquete_id, asiento_id)
);

-- ══════════════════════════════════════════════════════════
-- 7. ASIENTOS OCUPADOS POR FUNCIÓN
-- Tabla de control para evitar doble venta
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS funcion_asientos_ocupados (
    id          SERIAL PRIMARY KEY,
    funcion_id  INTEGER NOT NULL REFERENCES funciones(id) ON DELETE CASCADE,
    asiento_id  INTEGER NOT NULL REFERENCES asientos(id) ON DELETE CASCADE,
    tiquete_id  INTEGER NOT NULL REFERENCES tiquetes(id) ON DELETE CASCADE,
    -- RESTRICCIÓN CENTRAL: asiento único por función
    UNIQUE (funcion_id, asiento_id)
);

CREATE INDEX IF NOT EXISTS idx_fao_funcion  ON funcion_asientos_ocupados(funcion_id);
CREATE INDEX IF NOT EXISTS idx_fao_asiento  ON funcion_asientos_ocupados(asiento_id);

-- ══════════════════════════════════════════════════════════
-- 8. TARJETAS DE CRÉDITO/DÉBITO (por usuario)
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS tarjetas (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER     NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    ultimos_cuatro  CHAR(4)     NOT NULL,
    nombre_titular  VARCHAR(150) NOT NULL,
    fecha_expiracion VARCHAR(7)  NOT NULL,          -- MM/YYYY
    tipo            VARCHAR(30),                    -- Visa, Mastercard…
    activa          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMP   NOT NULL DEFAULT NOW(),
    -- Un usuario no puede registrar dos veces la misma terminación
    UNIQUE (usuario_id, ultimos_cuatro)
);

CREATE INDEX IF NOT EXISTS idx_tarjetas_usuario ON tarjetas(usuario_id);

-- ══════════════════════════════════════════════════════════
-- 9. SESIONES (opcional pero recomendado para producción)
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sesiones (
    id          VARCHAR(128) PRIMARY KEY,        -- token de sesión
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creada_en   TIMESTAMP NOT NULL DEFAULT NOW(),
    expira_en   TIMESTAMP NOT NULL DEFAULT NOW() + INTERVAL '7 days',
    ip          INET,
    user_agent  TEXT
);

CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON sesiones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_sesiones_expira  ON sesiones(expira_en);

-- ══════════════════════════════════════════════════════════
-- DATOS INICIALES
-- ══════════════════════════════════════════════════════════

-- Cuentas del equipo (contraseñas hasheadas con bcrypt en producción)
-- En desarrollo, el campo contrasena guarda el hash.
-- Usando pgcrypto: crypt('contraseña', gen_salt('bf'))
INSERT INTO usuarios (email, contrasena, nombre, rol, color, iniciales) VALUES
  ('jesusbarriosrodrig6@gmail.com',
   crypt('123456', gen_salt('bf')),
   'Jesús Barrios', '👑 Cuenta Principal', '#bf00ff', 'JB'),

  ('eilinsolano0123@gmail.com',
   crypt('987654321', gen_salt('bf')),
   'Eilin Solano', 'Usuario', '#00d4ff', 'ES'),

  ('matiasserrato156@gmail.com',
   crypt('matias serrato 123', gen_salt('bf')),
   'Matías Serrato', 'Usuario', '#ff006e', 'MS'),

  ('123kevindavidgomezposada@gmail.com',
   crypt('123456789', gen_salt('bf')),
   'Kevin Gómez', 'Usuario', '#00ff9f', 'KG')
ON CONFLICT (email) DO NOTHING;

-- ══════════════════════════════════════════════════════════
-- VISTAS ÚTILES
-- ══════════════════════════════════════════════════════════

-- Vista: tiquetes con información completa para "Mis Tiquetes"
CREATE OR REPLACE VIEW v_tiquetes_detalle AS
SELECT
    t.id,
    t.codigo_qr,
    t.usuario_id,
    u.nombre       AS usuario_nombre,
    u.email        AS usuario_email,
    t.funcion_id,
    p.titulo       AS pelicula_titulo,
    f.fecha        AS funcion_fecha,
    f.hora         AS funcion_hora,
    f.sala         AS funcion_sala,
    f.sede         AS funcion_sede,
    t.total,
    t.metodo_pago,
    t.combo_detalle,
    t.estado,
    t.comprado_en,
    -- Asientos como texto agrupado
    STRING_AGG(
        dt.fila || dt.numero || ' (' || dt.zona || ')',
        ', ' ORDER BY dt.zona, dt.fila, dt.numero
    ) AS asientos
FROM tiquetes t
JOIN usuarios  u  ON u.id = t.usuario_id
JOIN funciones f  ON f.id = t.funcion_id
JOIN peliculas p  ON p.id = f.pelicula_id
LEFT JOIN detalle_tiquete dt ON dt.tiquete_id = t.id
GROUP BY t.id, u.nombre, u.email, p.titulo, f.fecha, f.hora, f.sala, f.sede;

-- Vista: ocupación de sala por función
CREATE OR REPLACE VIEW v_ocupacion_funcion AS
SELECT
    f.id           AS funcion_id,
    p.titulo       AS pelicula,
    f.fecha,
    f.hora,
    f.sala,
    f.sede,
    COUNT(fao.asiento_id) AS asientos_ocupados,
    -- Capacidad: 72 asientos por zona × 3 zonas = 216 total (ajusta según tu sala)
    216 AS capacidad_total
FROM funciones f
JOIN peliculas p ON p.id = f.pelicula_id
LEFT JOIN funcion_asientos_ocupados fao ON fao.funcion_id = f.id
GROUP BY f.id, p.titulo;

-- ══════════════════════════════════════════════════════════
-- FUNCIÓN: verificar contraseña
-- Uso: SELECT verificar_login('email@test.com', 'mipass');
-- ══════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION verificar_login(p_email TEXT, p_pass TEXT)
RETURNS TABLE(id INTEGER, nombre VARCHAR, email VARCHAR, rol VARCHAR, color VARCHAR, iniciales VARCHAR)
LANGUAGE sql SECURITY DEFINER AS $$
    SELECT id, nombre, email, rol, color, iniciales
    FROM usuarios
    WHERE email = p_email
      AND contrasena = crypt(p_pass, contrasena)
      AND activo = TRUE
    LIMIT 1;
$$;

-- ══════════════════════════════════════════════════════════
-- FUNCIÓN: comprar tiquete (transacción segura)
-- Garantiza que no se venda dos veces el mismo asiento
-- ══════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION comprar_tiquete(
    p_codigo_qr     TEXT,
    p_usuario_id    INTEGER,
    p_funcion_id    INTEGER,
    p_metodo_pago   TEXT,
    p_total         NUMERIC,
    p_combo_detalle TEXT,
    p_asientos      JSONB   -- [{"asiento_id":1,"zona":"normal","fila":"A","numero":3,"precio":18000}, ...]
)
RETURNS INTEGER   -- retorna el id del tiquete creado
LANGUAGE plpgsql AS $$
DECLARE
    v_tiquete_id INTEGER;
    v_asiento    JSONB;
BEGIN
    -- Verificar que ningún asiento esté ya ocupado (bloqueo pesimista)
    IF EXISTS (
        SELECT 1 FROM funcion_asientos_ocupados fao
        WHERE fao.funcion_id = p_funcion_id
          AND fao.asiento_id IN (
              SELECT (elem->>'asiento_id')::INTEGER
              FROM jsonb_array_elements(p_asientos) AS elem
          )
        FOR UPDATE
    ) THEN
        RAISE EXCEPTION 'Uno o más asientos ya están ocupados para esta función.';
    END IF;

    -- Crear el tiquete
    INSERT INTO tiquetes (codigo_qr, usuario_id, funcion_id, metodo_pago, total, combo_detalle)
    VALUES (p_codigo_qr, p_usuario_id, p_funcion_id, p_metodo_pago, p_total, p_combo_detalle)
    RETURNING id INTO v_tiquete_id;

    -- Insertar cada asiento en detalle y en la tabla de ocupados
    FOR v_asiento IN SELECT * FROM jsonb_array_elements(p_asientos) LOOP
        INSERT INTO detalle_tiquete (tiquete_id, asiento_id, zona, fila, numero, precio)
        VALUES (
            v_tiquete_id,
            (v_asiento->>'asiento_id')::INTEGER,
            v_asiento->>'zona',
            (v_asiento->>'fila')::CHAR,
            (v_asiento->>'numero')::INTEGER,
            (v_asiento->>'precio')::NUMERIC
        );

        INSERT INTO funcion_asientos_ocupados (funcion_id, asiento_id, tiquete_id)
        VALUES (p_funcion_id, (v_asiento->>'asiento_id')::INTEGER, v_tiquete_id);
    END LOOP;

    RETURN v_tiquete_id;
END;
$$;

-- ══════════════════════════════════════════════════════════
-- ÍNDICES ADICIONALES DE RENDIMIENTO
-- ══════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_tiquetes_estado     ON tiquetes(estado);
CREATE INDEX IF NOT EXISTS idx_tiquetes_comprado   ON tiquetes(comprado_en DESC);
CREATE INDEX IF NOT EXISTS idx_detalle_tiquete_id  ON detalle_tiquete(tiquete_id);

-- ══════════════════════════════════════════════════════════
-- NOTAS DE INTEGRACIÓN CON FLASK (app.py)
-- ══════════════════════════════════════════════════════════
-- 1. Login:
--    SELECT * FROM verificar_login(%s, %s)
--
-- 2. Registro:
--    INSERT INTO usuarios (email, contrasena, nombre, color, iniciales)
--    VALUES (%s, crypt(%s, gen_salt('bf')), %s, %s, %s)
--
-- 3. Compra de tiquete:
--    SELECT comprar_tiquete(%s, %s, %s, %s, %s, %s, %s::jsonb)
--
-- 4. Mis tiquetes (por usuario):
--    SELECT * FROM v_tiquetes_detalle WHERE usuario_id = %s ORDER BY comprado_en DESC
--
-- 5. Validar QR:
--    SELECT * FROM v_tiquetes_detalle WHERE codigo_qr = %s
--
-- 6. Ocupación de sala:
--    SELECT asiento_id FROM funcion_asientos_ocupados WHERE funcion_id = %s
