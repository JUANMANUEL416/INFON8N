"""
Migración: Sistema de Aclaraciones y Validación de IA
Crea tablas para:
- Aclaraciones de campos de reportes
- Notificaciones para administradores
- Sistema de aprobación
"""
import psycopg2
import logging

logger = logging.getLogger(__name__)

def ejecutar_migracion(db_config):
    """Ejecutar migración del sistema de aclaraciones"""
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    try:
        # Tabla de aclaraciones de campos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS campo_aclaraciones (
                id SERIAL PRIMARY KEY,
                reporte_codigo VARCHAR(100) NOT NULL,
                nombre_campo VARCHAR(255) NOT NULL,
                pregunta_ia TEXT NOT NULL,
                respuesta_usuario TEXT,
                respuesta_admin TEXT,
                estado VARCHAR(50) DEFAULT 'pendiente',
                usuario_respondio VARCHAR(100),
                admin_respondio VARCHAR(100),
                fecha_pregunta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_respuesta_usuario TIMESTAMP,
                fecha_respuesta_admin TIMESTAMP,
                aprobado BOOLEAN DEFAULT FALSE,
                fecha_aprobacion TIMESTAMP,
                contexto_uso TEXT,
                puntuacion_utilidad INTEGER,
                UNIQUE(reporte_codigo, nombre_campo)
            );
        ''')
        
        # Índices para búsquedas rápidas
        cur.execute('''
            CREATE INDEX IF NOT EXISTS idx_aclaraciones_reporte 
            ON campo_aclaraciones(reporte_codigo);
        ''')
        
        cur.execute('''
            CREATE INDEX IF NOT EXISTS idx_aclaraciones_estado 
            ON campo_aclaraciones(estado);
        ''')
        
        # Tabla de notificaciones para administradores
        cur.execute('''
            CREATE TABLE IF NOT EXISTS notificaciones_admin (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(50) NOT NULL,
                titulo VARCHAR(255) NOT NULL,
                mensaje TEXT NOT NULL,
                datos JSONB,
                relacionado_con VARCHAR(20),
                relacionado_id INTEGER,
                leido BOOLEAN DEFAULT FALSE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_leido TIMESTAMP,
                admin_usuario VARCHAR(100)
            );
        ''')
        
        cur.execute('''
            CREATE INDEX IF NOT EXISTS idx_notificaciones_leido 
            ON notificaciones_admin(leido, fecha_creacion DESC);
        ''')
        
        # Tabla de validaciones de reportes por IA
        cur.execute('''
            CREATE TABLE IF NOT EXISTS reporte_validaciones_ia (
                id SERIAL PRIMARY KEY,
                reporte_codigo VARCHAR(100) NOT NULL,
                fecha_validacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validador_ia VARCHAR(50) DEFAULT 'gpt-4o',
                resultado JSONB NOT NULL,
                campos_dudosos JSONB,
                sugerencias JSONB,
                puntuacion_claridad DECIMAL(3,2),
                aprobado_por_ia BOOLEAN DEFAULT TRUE,
                comentarios_admin TEXT,
                validado_por VARCHAR(100)
            );
        ''')
        
        cur.execute('''
            CREATE INDEX IF NOT EXISTS idx_validaciones_reporte 
            ON reporte_validaciones_ia(reporte_codigo, fecha_validacion DESC);
        ''')
        
        # Tabla de historial de mejoras de la IA
        cur.execute('''
            CREATE TABLE IF NOT EXISTS ia_aprendizaje (
                id SERIAL PRIMARY KEY,
                tipo_aprendizaje VARCHAR(50) NOT NULL,
                contexto TEXT NOT NULL,
                pregunta_original TEXT,
                respuesta_mejorada TEXT NOT NULL,
                fuente VARCHAR(100),
                fecha_aprendido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                aplicado_en INTEGER DEFAULT 0,
                efectividad DECIMAL(3,2),
                tags JSONB,
                activo BOOLEAN DEFAULT TRUE
            );
        ''')
        
        cur.execute('''
            CREATE INDEX IF NOT EXISTS idx_aprendizaje_tipo 
            ON ia_aprendizaje(tipo_aprendizaje, activo);
        ''')
        
        conn.commit()
        logger.info("✅ Migración del sistema de aclaraciones completada")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error en migración: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import os
    
    # Configuración de base de datos desde variables de entorno
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'informes_db'),
        'user': os.getenv('DB_USER', 'admin'),
        'password': os.getenv('DB_PASSWORD', 'admin123'),
        'port': int(os.getenv('DB_PORT', 5432))
    }
    
    logging.basicConfig(level=logging.INFO)
    ejecutar_migracion(db_config)
