"""
Migración: Agregar control de periodos y validación de cargas
Versión actualizada para esquema real (reportes_config, datos_reportes)
"""

MIGRATION_SQL = """
BEGIN;

-- 1. Agregar campos de control de periodo a reportes_config
ALTER TABLE reportes_config 
ADD COLUMN IF NOT EXISTS tipo_periodo VARCHAR(20) DEFAULT 'libre',
ADD COLUMN IF NOT EXISTS campo_fecha VARCHAR(100),
ADD COLUMN IF NOT EXISTS requiere_periodo BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS validacion_ia JSONB,
ADD COLUMN IF NOT EXISTS estado_validacion VARCHAR(20) DEFAULT 'pendiente';

COMMENT ON COLUMN reportes_config.tipo_periodo IS 'Tipo de periodo: libre, diario, semanal, quincenal, mensual, trimestral, anual';
COMMENT ON COLUMN reportes_config.campo_fecha IS 'Nombre del campo que contiene la fecha para validación de periodo';
COMMENT ON COLUMN reportes_config.requiere_periodo IS 'Si requiere control de periodos para carga';
COMMENT ON COLUMN reportes_config.validacion_ia IS 'Resultado de validación de IA al crear el reporte';
COMMENT ON COLUMN reportes_config.estado_validacion IS 'Estado: pendiente, validado, rechazado';

-- 2. Agregar campos a datos_reportes para tracking de carga
ALTER TABLE datos_reportes
ADD COLUMN IF NOT EXISTS carga_id INTEGER,
ADD COLUMN IF NOT EXISTS fecha_periodo DATE,
ADD COLUMN IF NOT EXISTS periodo_inicio DATE,
ADD COLUMN IF NOT EXISTS periodo_fin DATE;

CREATE INDEX IF NOT EXISTS idx_datos_periodo ON datos_reportes(periodo_inicio, periodo_fin);
CREATE INDEX IF NOT EXISTS idx_datos_carga ON datos_reportes(carga_id);
CREATE INDEX IF NOT EXISTS idx_datos_fecha_periodo ON datos_reportes(fecha_periodo);

COMMENT ON COLUMN datos_reportes.carga_id IS 'Referencia a la carga que insertó estos datos';
COMMENT ON COLUMN datos_reportes.fecha_periodo IS 'Fecha del periodo extraída de los datos';
COMMENT ON COLUMN datos_reportes.periodo_inicio IS 'Inicio del periodo calculado';
COMMENT ON COLUMN datos_reportes.periodo_fin IS 'Fin del periodo calculado';

-- 3. Crear tabla de cargas de datos (historial mejorado)
CREATE TABLE IF NOT EXISTS cargas_datos (
    id SERIAL PRIMARY KEY,
    reporte_codigo VARCHAR(100) NOT NULL,
    periodo_inicio DATE NOT NULL,
    periodo_fin DATE NOT NULL,
    periodo_tipo VARCHAR(20) NOT NULL,
    cantidad_registros INTEGER NOT NULL DEFAULT 0,
    archivo_original VARCHAR(255),
    usuario_carga VARCHAR(100),
    estado VARCHAR(20) DEFAULT 'pendiente',
    validacion_previa JSONB,
    errores_validacion TEXT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_aprobacion TIMESTAMP,
    aprobado_por VARCHAR(100),
    notas TEXT,
    CONSTRAINT unique_periodo_reporte UNIQUE(reporte_codigo, periodo_inicio, periodo_fin),
    CONSTRAINT fk_reporte FOREIGN KEY (reporte_codigo) REFERENCES reportes_config(codigo) ON DELETE CASCADE
);

CREATE INDEX idx_cargas_reporte ON cargas_datos(reporte_codigo);
CREATE INDEX idx_cargas_periodo ON cargas_datos(periodo_inicio, periodo_fin);
CREATE INDEX idx_cargas_estado ON cargas_datos(estado);
CREATE INDEX idx_cargas_fecha ON cargas_datos(fecha_carga);

COMMENT ON TABLE cargas_datos IS 'Historial de cargas de datos por reporte y periodo';
COMMENT ON COLUMN cargas_datos.estado IS 'pendiente, validado, aprobado, rechazado';
COMMENT ON COLUMN cargas_datos.validacion_previa IS 'Resultado de validación de IA antes de aprobación';

-- 4. Crear tabla de registros temporales (staging antes de aprobar)
CREATE TABLE IF NOT EXISTS datos_temporales (
    id SERIAL PRIMARY KEY,
    carga_id INTEGER NOT NULL,
    reporte_codigo VARCHAR(100) NOT NULL,
    datos JSONB NOT NULL,
    fila_numero INTEGER,
    fecha_extraida DATE,
    periodo_inicio DATE,
    periodo_fin DATE,
    errores JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_carga FOREIGN KEY (carga_id) REFERENCES cargas_datos(id) ON DELETE CASCADE,
    CONSTRAINT fk_reporte_temp FOREIGN KEY (reporte_codigo) REFERENCES reportes_config(codigo) ON DELETE CASCADE
);

CREATE INDEX idx_temporales_carga ON datos_temporales(carga_id);
CREATE INDEX idx_temporales_reporte ON datos_temporales(reporte_codigo);
CREATE INDEX idx_temporales_fecha ON datos_temporales(fecha_extraida);
CREATE INDEX idx_temporales_periodo ON datos_temporales(periodo_inicio, periodo_fin);

COMMENT ON TABLE datos_temporales IS 'Datos temporales pendientes de aprobación del administrador';
COMMENT ON COLUMN datos_temporales.errores IS 'Errores de validación encontrados en este registro';

-- 5. Crear vista de resumen de cargas
CREATE OR REPLACE VIEW v_resumen_cargas AS
SELECT 
    c.id,
    c.reporte_codigo,
    rc.nombre as reporte_nombre,
    c.periodo_tipo,
    c.periodo_inicio,
    c.periodo_fin,
    c.cantidad_registros,
    c.estado,
    c.usuario_carga,
    c.fecha_carga,
    c.fecha_aprobacion,
    c.aprobado_por,
    c.archivo_original,
    (SELECT COUNT(*) FROM datos_temporales WHERE carga_id = c.id) as registros_pendientes,
    (SELECT COUNT(*) FROM datos_reportes WHERE carga_id = c.id) as registros_aprobados
FROM cargas_datos c
LEFT JOIN reportes_config rc ON c.reporte_codigo = rc.codigo
ORDER BY c.fecha_carga DESC;

COMMENT ON VIEW v_resumen_cargas IS 'Vista resumen de cargas con estado actual';

-- 6. Función para validar periodos (no duplicados/overlaps)
CREATE OR REPLACE FUNCTION validar_periodo(
    p_reporte_codigo VARCHAR,
    p_periodo_inicio DATE,
    p_periodo_fin DATE,
    p_carga_id INTEGER DEFAULT NULL
)
RETURNS TABLE(
    valido BOOLEAN,
    mensaje TEXT,
    cargas_conflicto INTEGER[]
) AS $$
DECLARE
    conflictos INTEGER[];
BEGIN
    -- Buscar cargas que se solapan con el periodo propuesto
    -- Excluir la carga actual si se está editando
    SELECT ARRAY_AGG(id) INTO conflictos
    FROM cargas_datos
    WHERE reporte_codigo = p_reporte_codigo
    AND estado IN ('aprobado', 'validado')
    AND (p_carga_id IS NULL OR id != p_carga_id)
    AND (
        -- Overlap: inicio del nuevo está dentro de periodo existente
        (p_periodo_inicio >= periodo_inicio AND p_periodo_inicio <= periodo_fin)
        OR
        -- Overlap: fin del nuevo está dentro de periodo existente
        (p_periodo_fin >= periodo_inicio AND p_periodo_fin <= periodo_fin)
        OR
        -- Overlap: nuevo periodo contiene completamente al existente
        (p_periodo_inicio <= periodo_inicio AND p_periodo_fin >= periodo_fin)
    );
    
    IF conflictos IS NOT NULL AND array_length(conflictos, 1) > 0 THEN
        RETURN QUERY SELECT 
            false,
            'El periodo se solapa con cargas existentes: ' || array_to_string(conflictos, ', '),
            conflictos;
    ELSE
        RETURN QUERY SELECT 
            true,
            'Periodo válido - no hay solapamientos',
            ARRAY[]::INTEGER[];
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validar_periodo IS 'Valida que un periodo no se solape con cargas ya aprobadas';

-- 7. Función para calcular rangos de periodo basado en tipo y fecha
CREATE OR REPLACE FUNCTION calcular_periodo(
    p_tipo_periodo VARCHAR,
    p_fecha DATE
)
RETURNS TABLE(
    periodo_inicio DATE,
    periodo_fin DATE
) AS $$
BEGIN
    CASE p_tipo_periodo
        WHEN 'diario' THEN
            RETURN QUERY SELECT p_fecha, p_fecha;
        WHEN 'semanal' THEN
            RETURN QUERY SELECT 
                (DATE_TRUNC('week', p_fecha::TIMESTAMP))::DATE,
                (DATE_TRUNC('week', p_fecha::TIMESTAMP) + INTERVAL '6 days')::DATE;
        WHEN 'quincenal' THEN
            -- Primera quincena: día 1-15, segunda quincena: día 16-fin de mes
            IF EXTRACT(DAY FROM p_fecha) <= 15 THEN
                RETURN QUERY SELECT 
                    DATE_TRUNC('month', p_fecha::TIMESTAMP)::DATE,
                    (DATE_TRUNC('month', p_fecha::TIMESTAMP) + INTERVAL '14 days')::DATE;
            ELSE
                RETURN QUERY SELECT 
                    (DATE_TRUNC('month', p_fecha::TIMESTAMP) + INTERVAL '15 days')::DATE,
                    (DATE_TRUNC('month', p_fecha::TIMESTAMP) + INTERVAL '1 month - 1 day')::DATE;
            END IF;
        WHEN 'mensual' THEN
            RETURN QUERY SELECT 
                DATE_TRUNC('month', p_fecha::TIMESTAMP)::DATE,
                (DATE_TRUNC('month', p_fecha::TIMESTAMP) + INTERVAL '1 month - 1 day')::DATE;
        WHEN 'trimestral' THEN
            RETURN QUERY SELECT 
                DATE_TRUNC('quarter', p_fecha::TIMESTAMP)::DATE,
                (DATE_TRUNC('quarter', p_fecha::TIMESTAMP) + INTERVAL '3 months - 1 day')::DATE;
        WHEN 'anual' THEN
            RETURN QUERY SELECT 
                DATE_TRUNC('year', p_fecha::TIMESTAMP)::DATE,
                (DATE_TRUNC('year', p_fecha::TIMESTAMP) + INTERVAL '1 year - 1 day')::DATE;
        ELSE
            -- Tipo 'libre' u otro: sin restricción
            RETURN QUERY SELECT p_fecha, p_fecha;
    END CASE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calcular_periodo IS 'Calcula el rango de fechas para un periodo basado en su tipo';

-- 8. Trigger para actualizar automáticamente periodo en datos_temporales
CREATE OR REPLACE FUNCTION actualizar_periodo_temporal()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo_periodo VARCHAR;
    v_campo_fecha VARCHAR;
    v_fecha DATE;
    v_periodo_calc RECORD;
BEGIN
    -- Obtener configuración del reporte
    SELECT tipo_periodo, campo_fecha
    INTO v_tipo_periodo, v_campo_fecha
    FROM reportes_config
    WHERE codigo = NEW.reporte_codigo;
    
    -- Si tiene configuración de periodo, calcular
    IF v_tipo_periodo IS NOT NULL AND v_tipo_periodo != 'libre' THEN
        -- Extraer fecha del campo especificado
        IF v_campo_fecha IS NOT NULL THEN
            v_fecha := (NEW.datos->>v_campo_fecha)::DATE;
            NEW.fecha_extraida := v_fecha;
            
            -- Calcular periodo
            SELECT * INTO v_periodo_calc
            FROM calcular_periodo(v_tipo_periodo, v_fecha);
            
            NEW.periodo_inicio := v_periodo_calc.periodo_inicio;
            NEW.periodo_fin := v_periodo_calc.periodo_fin;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_actualizar_periodo_temporal
BEFORE INSERT ON datos_temporales
FOR EACH ROW
EXECUTE FUNCTION actualizar_periodo_temporal();

COMMENT ON FUNCTION actualizar_periodo_temporal IS 'Trigger que calcula automáticamente el periodo al insertar en datos_temporales';

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
        
        print("Ejecutando migración de control de periodos v2...")
        print("=" * 60)
        cur.execute(MIGRATION_SQL)
        conn.commit()
        
        print("\n✓ Migración completada exitosamente\n")
        print("Cambios aplicados:")
        print("  ✓ Agregados campos de periodo a reportes_config")
        print("  ✓ Agregados campos de tracking a datos_reportes")
        print("  ✓ Tabla cargas_datos creada")
        print("  ✓ Tabla datos_temporales creada (staging)")
        print("  ✓ Vista v_resumen_cargas creada")
        print("  ✓ Función validar_periodo() creada")
        print("  ✓ Función calcular_periodo() creada")
        print("  ✓ Trigger para cálculo automático de periodos creado")
        print("\n" + "=" * 60)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Error en migración: {e}")
        if 'conn' in locals():
            conn.rollback()
        import traceback
        traceback.print_exc()
        exit(1)
