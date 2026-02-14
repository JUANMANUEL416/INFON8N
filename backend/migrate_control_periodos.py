"""
Migración: Agregar control de periodos y validación de cargas
"""

MIGRATION_SQL = """
-- 1. Agregar campos de control de periodo a reportes
ALTER TABLE reportes 
ADD COLUMN IF NOT EXISTS tipo_periodo VARCHAR(20) DEFAULT 'libre',
ADD COLUMN IF NOT EXISTS campo_fecha VARCHAR(100),
ADD COLUMN IF NOT EXISTS validacion_ia TEXT,
ADD COLUMN IF NOT EXISTS estado_validacion VARCHAR(20) DEFAULT 'pendiente';

COMMENT ON COLUMN reportes.tipo_periodo IS 'Tipo de periodo: libre, diario, semanal, quincenal, mensual, trimestral, anual';
COMMENT ON COLUMN reportes.campo_fecha IS 'Nombre del campo que contiene la fecha para validación de periodo';
COMMENT ON COLUMN reportes.validacion_ia IS 'Resultado de validación de IA al crear el reporte';
COMMENT ON COLUMN reportes.estado_validacion IS 'Estado: pendiente, validado, rechazado';

-- 2. Crear tabla de cargas de datos (historial)
CREATE TABLE IF NOT EXISTS cargas_datos (
    id SERIAL PRIMARY KEY,
    reporte_codigo VARCHAR(100) NOT NULL REFERENCES reportes(codigo) ON DELETE CASCADE,
    periodo_inicio DATE NOT NULL,
    periodo_fin DATE NOT NULL,
    periodo_tipo VARCHAR(20) NOT NULL,
    cantidad_registros INTEGER NOT NULL DEFAULT 0,
    archivo_original VARCHAR(255),
    usuario_carga VARCHAR(100),
    estado VARCHAR(20) DEFAULT 'pendiente',
    validacion_previa TEXT,
    errores_validacion TEXT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_aprobacion TIMESTAMP,
    aprobado_por VARCHAR(100),
    CONSTRAINT unique_periodo_reporte UNIQUE(reporte_codigo, periodo_inicio, periodo_fin)
);

CREATE INDEX idx_cargas_reporte ON cargas_datos(reporte_codigo);
CREATE INDEX idx_cargas_periodo ON cargas_datos(periodo_inicio, periodo_fin);
CREATE INDEX idx_cargas_estado ON cargas_datos(estado);

COMMENT ON TABLE cargas_datos IS 'Historial de cargas de datos por reporte y periodo';
COMMENT ON COLUMN cargas_datos.estado IS 'pendiente, validado, aprobado, rechazado';

-- 3. Crear tabla de registros temporales (antes de aprobar)
CREATE TABLE IF NOT EXISTS datos_temporales (
    id SERIAL PRIMARY KEY,
    carga_id INTEGER NOT NULL REFERENCES cargas_datos(id) ON DELETE CASCADE,
    reporte_codigo VARCHAR(100) NOT NULL,
    datos JSONB NOT NULL,
    fila_numero INTEGER,
    fecha_registro DATE,
    errores TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_temporales_carga ON datos_temporales(carga_id);
CREATE INDEX idx_temporales_reporte ON datos_temporales(reporte_codigo);
CREATE INDEX idx_temporales_fecha ON datos_temporales(fecha_registro);

COMMENT ON TABLE datos_temporales IS 'Datos temporales pendientes de aprobación';

-- 4. Agregar campos de auditoría a tablas dinámicas (se aplicará vía código)
-- Las tablas dinámicas deben tener estos campos:
--   periodo_inicio DATE
--   periodo_fin DATE  
--   carga_id INTEGER REFERENCES cargas_datos(id)
--   fecha_carga TIMESTAMP

-- 5. Crear vista de resumen de cargas
CREATE OR REPLACE VIEW v_resumen_cargas AS
SELECT 
    r.nombre as reporte_nombre,
    r.codigo as reporte_codigo,
    r.tipo_periodo,
    cd.id as carga_id,
    cd.periodo_inicio,
    cd.periodo_fin,
    cd.periodo_tipo,
    cd.cantidad_registros,
    cd.estado,
    cd.usuario_carga,
    cd.fecha_carga,
    cd.fecha_aprobacion,
    cd.aprobado_por,
    CASE 
        WHEN cd.estado = 'aprobado' THEN 'Aprobado'
        WHEN cd.estado = 'rechazado' THEN 'Rechazado'
        WHEN cd.estado = 'validado' THEN 'Validado - Pendiente Aprobación'
        ELSE 'Pendiente Validación'
    END as estado_descripcion
FROM reportes r
LEFT JOIN cargas_datos cd ON r.codigo = cd.reporte_codigo
ORDER BY cd.fecha_carga DESC;

-- 6. Función para validar periodo
CREATE OR REPLACE FUNCTION validar_periodo(
    p_reporte_codigo VARCHAR,
    p_periodo_inicio DATE,
    p_periodo_fin DATE
) RETURNS TABLE(valido BOOLEAN, mensaje TEXT) AS $$
DECLARE
    v_existe INTEGER;
    v_tipo_periodo VARCHAR;
BEGIN
    -- Obtener tipo de periodo del reporte
    SELECT tipo_periodo INTO v_tipo_periodo
    FROM reportes
    WHERE codigo = p_reporte_codigo;
    
    -- Si el reporte es de tipo 'libre', siempre es válido
    IF v_tipo_periodo = 'libre' THEN
        RETURN QUERY SELECT TRUE, 'Periodo libre, sin restricciones'::TEXT;
        RETURN;
    END IF;
    
    -- Validar que no exista un periodo con los mismos rangos
    SELECT COUNT(*) INTO v_existe
    FROM cargas_datos
    WHERE reporte_codigo = p_reporte_codigo
      AND periodo_inicio = p_periodo_inicio
      AND periodo_fin = p_periodo_fin
      AND estado IN ('validado', 'aprobado');
    
    IF v_existe > 0 THEN
        RETURN QUERY SELECT FALSE, 'Ya existe una carga para este periodo'::TEXT;
        RETURN;
    END IF;
    
    -- Validar que no haya solapamiento de periodos
    SELECT COUNT(*) INTO v_existe
    FROM cargas_datos
    WHERE reporte_codigo = p_reporte_codigo
      AND estado IN ('validado', 'aprobado')
      AND (
          (periodo_inicio <= p_periodo_inicio AND periodo_fin >= p_periodo_inicio) OR
          (periodo_inicio <= p_periodo_fin AND periodo_fin >= p_periodo_fin) OR
          (periodo_inicio >= p_periodo_inicio AND periodo_fin <= p_periodo_fin)
      );
    
    IF v_existe > 0 THEN
        RETURN QUERY SELECT FALSE, 'El periodo se solapa con una carga existente'::TEXT;
        RETURN;
    END IF;
    
    RETURN QUERY SELECT TRUE, 'Periodo válido'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- 7. Función para calcular periodo según tipo
CREATE OR REPLACE FUNCTION calcular_periodo(
    p_fecha DATE,
    p_tipo_periodo VARCHAR
) RETURNS TABLE(inicio DATE, fin DATE) AS $$
BEGIN
    CASE p_tipo_periodo
        WHEN 'diario' THEN
            RETURN QUERY SELECT p_fecha, p_fecha;
        WHEN 'semanal' THEN
            RETURN QUERY SELECT 
                DATE_TRUNC('week', p_fecha)::DATE,
                (DATE_TRUNC('week', p_fecha) + INTERVAL '6 days')::DATE;
        WHEN 'quincenal' THEN
            IF EXTRACT(DAY FROM p_fecha) <= 15 THEN
                RETURN QUERY SELECT 
                    DATE_TRUNC('month', p_fecha)::DATE,
                    (DATE_TRUNC('month', p_fecha) + INTERVAL '14 days')::DATE;
            ELSE
                RETURN QUERY SELECT 
                    (DATE_TRUNC('month', p_fecha) + INTERVAL '15 days')::DATE,
                    (DATE_TRUNC('month', p_fecha) + INTERVAL '1 month - 1 day')::DATE;
            END IF;
        WHEN 'mensual' THEN
            RETURN QUERY SELECT 
                DATE_TRUNC('month', p_fecha)::DATE,
                (DATE_TRUNC('month', p_fecha) + INTERVAL '1 month - 1 day')::DATE;
        WHEN 'trimestral' THEN
            RETURN QUERY SELECT 
                DATE_TRUNC('quarter', p_fecha)::DATE,
                (DATE_TRUNC('quarter', p_fecha) + INTERVAL '3 months - 1 day')::DATE;
        WHEN 'anual' THEN
            RETURN QUERY SELECT 
                DATE_TRUNC('year', p_fecha)::DATE,
                (DATE_TRUNC('year', p_fecha) + INTERVAL '1 year - 1 day')::DATE;
        ELSE
            RETURN QUERY SELECT p_fecha, p_fecha;
    END CASE;
END;
$$ LANGUAGE plpgsql;

COMMIT;
"""

if __name__ == '__main__':
    import psycopg2
    import os
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'informes_db'),
        'user': os.getenv('DB_USER', 'admin'),
        'password': os.getenv('DB_PASSWORD', 'admin123')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        conn.autocommit = False
        cur = conn.cursor()
        
        print("Ejecutando migración de control de periodos...")
        cur.execute(MIGRATION_SQL)
        conn.commit()
        
        print("✓ Migración completada exitosamente")
        print("  - Agregados campos de periodo a reportes")
        print("  - Tabla cargas_datos creada")
        print("  - Tabla datos_temporales creada")
        print("  - Vista v_resumen_cargas creada")
        print("  - Funciones de validación creadas")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error en migración: {e}")
        if conn:
            conn.rollback()
        exit(1)
