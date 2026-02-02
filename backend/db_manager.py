"""
Gestor de base de datos dinámico
Crea y gestiona tablas automáticamente según configuración de reportes
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json
from typing import List, Dict, Optional
from models import ReporteConfig, CampoConfig

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestor dinámico de base de datos"""
    
    def __init__(self, db_config):
        self.db_config = db_config
    
    def get_connection(self):
        """Obtener conexión a BD"""
        return psycopg2.connect(**self.db_config)
    
    def init_metadata_tables(self):
        """Crear tablas de metadatos del sistema"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Tabla de configuración de reportes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS reportes_config (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    codigo VARCHAR(100) UNIQUE NOT NULL,
                    descripcion TEXT,
                    contexto TEXT,
                    categoria VARCHAR(100),
                    icono VARCHAR(20),
                    activo BOOLEAN DEFAULT TRUE,
                    campos JSONB,
                    relaciones JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100)
                );
            ''')
            
            # Tabla de datos genérica (para almacenar todos los reportes)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS datos_reportes (
                    id SERIAL PRIMARY KEY,
                    reporte_codigo VARCHAR(100) NOT NULL,
                    datos JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uploaded_by VARCHAR(100)
                );
            ''')
            
            # Índice para búsquedas rápidas
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_datos_reportes_codigo 
                ON datos_reportes(reporte_codigo);
            ''')
            
            # Tabla de logs de carga
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cargas_log (
                    id SERIAL PRIMARY KEY,
                    reporte_codigo VARCHAR(100),
                    nombre_archivo VARCHAR(255),
                    registros_insertados INTEGER,
                    registros_error INTEGER,
                    estado VARCHAR(50),
                    mensaje TEXT,
                    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario VARCHAR(100)
                );
            ''')
            
            # Tabla de usuarios (básica)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    nombre_completo VARCHAR(255),
                    rol VARCHAR(50) DEFAULT 'usuario',
                    activo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Insertar usuario admin por defecto
            cur.execute('''
                INSERT INTO usuarios (username, nombre_completo, rol)
                VALUES ('admin', 'Administrador', 'admin')
                ON CONFLICT (username) DO NOTHING;
            ''')
            
            conn.commit()
            logger.info("Tablas de metadatos creadas correctamente")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando tablas de metadatos: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    
    def crear_reporte(self, reporte_config: ReporteConfig):
        """Crear nuevo reporte en el sistema"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Guardar configuración del reporte
            cur.execute('''
                INSERT INTO reportes_config 
                (nombre, codigo, descripcion, contexto, categoria, icono, campos, relaciones, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                reporte_config.nombre,
                reporte_config.codigo,
                reporte_config.descripcion,
                reporte_config.contexto,
                reporte_config.categoria,
                reporte_config.icono,
                json.dumps(reporte_config.campos),
                json.dumps(reporte_config.relaciones),
                'admin'
            ))
            
            reporte_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"Reporte '{reporte_config.nombre}' creado con ID {reporte_id}")
            return reporte_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando reporte: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def obtener_reporte(self, codigo: str) -> Optional[Dict]:
        """Obtener configuración de un reporte"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute('''
                SELECT * FROM reportes_config 
                WHERE codigo = %s AND activo = TRUE
            ''', (codigo,))
            
            result = cur.fetchone()
            return dict(result) if result else None
            
        finally:
            cur.close()
            conn.close()
    
    def listar_reportes(self, solo_activos=True) -> List[Dict]:
        """Listar todos los reportes"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            query = 'SELECT * FROM reportes_config'
            if solo_activos:
                query += ' WHERE activo = TRUE'
            query += ' ORDER BY categoria, nombre'
            
            cur.execute(query)
            return [dict(row) for row in cur.fetchall()]
            
        finally:
            cur.close()
            conn.close()
    
    def actualizar_reporte(self, codigo: str, datos: Dict):
        """Actualizar configuración de reporte"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            campos_update = []
            valores = []
            
            if 'nombre' in datos:
                campos_update.append('nombre = %s')
                valores.append(datos['nombre'])
            if 'descripcion' in datos:
                campos_update.append('descripcion = %s')
                valores.append(datos['descripcion'])
            if 'contexto' in datos:
                campos_update.append('contexto = %s')
                valores.append(datos['contexto'])
            if 'campos' in datos:
                campos_update.append('campos = %s')
                valores.append(json.dumps(datos['campos']))
            if 'relaciones' in datos:
                campos_update.append('relaciones = %s')
                valores.append(json.dumps(datos['relaciones']))
            
            campos_update.append('updated_at = CURRENT_TIMESTAMP')
            valores.append(codigo)
            
            query = f'''
                UPDATE reportes_config 
                SET {', '.join(campos_update)}
                WHERE codigo = %s
            '''
            
            cur.execute(query, valores)
            conn.commit()
            
            logger.info(f"Reporte '{codigo}' actualizado")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error actualizando reporte: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    
    def insertar_datos(self, reporte_codigo: str, datos_lista: List[Dict], usuario='sistema'):
        """Insertar datos de un reporte"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            registros_ok = 0
            registros_error = 0
            
            for datos in datos_lista:
                try:
                    cur.execute('''
                        INSERT INTO datos_reportes (reporte_codigo, datos, uploaded_by)
                        VALUES (%s, %s, %s)
                    ''', (reporte_codigo, json.dumps(datos), usuario))
                    registros_ok += 1
                except Exception as e:
                    logger.error(f"Error insertando registro: {e}")
                    registros_error += 1
            
            conn.commit()
            logger.info(f"Insertados {registros_ok} registros en '{reporte_codigo}'")
            
            return {
                'registros_insertados': registros_ok,
                'registros_error': registros_error
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error insertando datos: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def consultar_datos(self, reporte_codigo: str, filtros: Optional[Dict] = None, limite=100):
        """Consultar datos de un reporte"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            query = '''
                SELECT id, datos, created_at, uploaded_by 
                FROM datos_reportes 
                WHERE reporte_codigo = %s
            '''
            params = [reporte_codigo]
            
            # Aquí se podrían agregar filtros JSONB
            
            query += ' ORDER BY created_at DESC LIMIT %s'
            params.append(limite)
            
            cur.execute(query, params)
            
            resultados = []
            for row in cur.fetchall():
                resultado = dict(row)
                resultado['datos'] = row['datos']  # Ya es un dict por JSONB
                resultados.append(resultado)
            
            return resultados
            
        finally:
            cur.close()
            conn.close()
    
    def obtener_estadisticas(self, reporte_codigo: str) -> Dict:
        """Obtener estadísticas de un reporte"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute('''
                SELECT 
                    COUNT(*) as total_registros,
                    MIN(created_at) as primera_carga,
                    MAX(created_at) as ultima_carga
                FROM datos_reportes
                WHERE reporte_codigo = %s
            ''', (reporte_codigo,))
            
            return dict(cur.fetchone())
            
        finally:
            cur.close()
            conn.close()
