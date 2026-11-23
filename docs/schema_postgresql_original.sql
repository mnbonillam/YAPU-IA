-- YAPU - Esquema base de base de datos (Integrante 5)
-- Solo modelado SQL. Sin lógica de aplicación.

-- Extensiones (opcional según motor; ajustar si se usa MySQL)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- =========================
-- USUARIOS Y ADMINISTRACIÓN
-- =========================
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rol_id INT NOT NULL REFERENCES roles(id),
    nombre_completo VARCHAR(150) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    telefono VARCHAR(30),
    contrasena_hash VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_acceso TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE permisos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE rol_permisos (
    rol_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permiso_id INT NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
    PRIMARY KEY (rol_id, permiso_id)
);

CREATE TABLE sesiones_admin (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expira_en TIMESTAMP NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- PRODUCTORES Y PARCELAS
-- =========================
CREATE TABLE productores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_admin_id UUID REFERENCES usuarios(id),
    nombre_completo VARCHAR(150) NOT NULL,
    telefono VARCHAR(30),
    zona VARCHAR(120),
    comunidad VARCHAR(120),
    estado VARCHAR(30) NOT NULL DEFAULT 'activo',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE parcelas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    productor_id UUID NOT NULL REFERENCES productores(id) ON DELETE CASCADE,
    nombre VARCHAR(120) NOT NULL,
    cultivo VARCHAR(100) NOT NULL,
    latitud DECIMAL(10,7),
    longitud DECIMAL(10,7),
    area_ha DECIMAL(10,2),
    altitud_m DECIMAL(10,2),
    estado VARCHAR(30) NOT NULL DEFAULT 'activa',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- CLIMA Y RIESGOS
-- =========================
CREATE TABLE registros_clima (
    id BIGSERIAL PRIMARY KEY,
    parcela_id UUID NOT NULL REFERENCES parcelas(id) ON DELETE CASCADE,
    fuente VARCHAR(80),
    temperatura_c DECIMAL(5,2),
    humedad_pct DECIMAL(5,2),
    precipitacion_mm DECIMAL(8,2),
    probabilidad_lluvia_pct DECIMAL(5,2),
    viento_kmh DECIMAL(6,2),
    fecha_hora TIMESTAMP NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evaluaciones_riesgo (
    id BIGSERIAL PRIMARY KEY,
    parcela_id UUID NOT NULL REFERENCES parcelas(id) ON DELETE CASCADE,
    registro_clima_id BIGINT REFERENCES registros_clima(id) ON DELETE SET NULL,
    tipo_riesgo VARCHAR(60) NOT NULL, -- helada, sequia, lluvia, viento, etc.
    nivel VARCHAR(20) NOT NULL,       -- bajo, medio, alto
    probabilidad_pct DECIMAL(5,2),
    evidencia TEXT,
    recomendacion TEXT,
    estado VARCHAR(30) NOT NULL DEFAULT 'activa',
    evaluado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE alertas (
    id BIGSERIAL PRIMARY KEY,
    parcela_id UUID NOT NULL REFERENCES parcelas(id) ON DELETE CASCADE,
    productor_id UUID NOT NULL REFERENCES productores(id) ON DELETE CASCADE,
    evaluacion_riesgo_id BIGINT REFERENCES evaluaciones_riesgo(id) ON DELETE SET NULL,
    tipo_riesgo VARCHAR(60) NOT NULL,
    nivel VARCHAR(20) NOT NULL,
    mensaje TEXT NOT NULL,
    canal VARCHAR(30) NOT NULL DEFAULT 'simulado',
    estado VARCHAR(30) NOT NULL DEFAULT 'pendiente', -- pendiente, enviada, atendida
    enviada_en TIMESTAMP,
    creada_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bitacora_mensajes (
    id BIGSERIAL PRIMARY KEY,
    alerta_id BIGINT REFERENCES alertas(id) ON DELETE SET NULL,
    productor_id UUID NOT NULL REFERENCES productores(id) ON DELETE CASCADE,
    direccion VARCHAR(20) NOT NULL, -- entrante, saliente
    contenido TEXT NOT NULL,
    canal VARCHAR(30) NOT NULL DEFAULT 'simulado',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- CONTENIDOS Y MÉTRICAS (PANEL ADMIN)
-- =========================
CREATE TABLE contenidos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    titulo VARCHAR(200) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- guia, recomendacion, noticia, faq
    cuerpo TEXT NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'borrador', -- borrador, publicado, archivado
    publicado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE metricas_panel (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    valor DECIMAL(14,2) NOT NULL,
    unidad VARCHAR(30),
    periodo_inicio DATE,
    periodo_fin DATE,
    fuente VARCHAR(80),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE eventos_auditoria (
    id BIGSERIAL PRIMARY KEY,
    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    accion VARCHAR(120) NOT NULL,
    entidad VARCHAR(80),
    entidad_id VARCHAR(80),
    detalle TEXT,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- VECTORIAL (BÚSQUEDA/CONTEXTO)
-- =========================
CREATE TABLE documentos_vectoriales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contenido_id UUID REFERENCES contenidos(id) ON DELETE CASCADE,
    titulo VARCHAR(200),
    texto TEXT NOT NULL,
    embedding vector(1536), -- ajustar dimensión según modelo elegido
    metadata JSONB,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices sugeridos
CREATE INDEX idx_usuarios_rol ON usuarios(rol_id);
CREATE INDEX idx_parcelas_productor ON parcelas(productor_id);
CREATE INDEX idx_clima_parcela_fecha ON registros_clima(parcela_id, fecha_hora DESC);
CREATE INDEX idx_riesgo_parcela_fecha ON evaluaciones_riesgo(parcela_id, evaluado_en DESC);
CREATE INDEX idx_alertas_productor_estado ON alertas(productor_id, estado);
CREATE INDEX idx_contenidos_estado ON contenidos(estado);
CREATE INDEX idx_metricas_nombre_periodo ON metricas_panel(nombre, periodo_inicio, periodo_fin);
CREATE INDEX idx_documentos_vectoriales_contenido ON documentos_vectoriales(contenido_id);
-- Índice vectorial (ejemplo para pgvector; ajustar según método/distancia)
-- CREATE INDEX idx_documentos_embedding ON documentos_vectoriales USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
