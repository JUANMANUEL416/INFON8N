"""
Gestor de base de datos dinámico
Crea y gestiona tablas automáticamente según configuración de reportes
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json
import pandas as pd
from datetime import datetime
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
                    relaciones JSONB,                    api_endpoint VARCHAR(255),
                    query_template TEXT,                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            
            # Tabla de grupos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS grupos (
                    id SERIAL PRIMARY KEY,
                    codigo VARCHAR(100) UNIQUE NOT NULL,
                    nombre VARCHAR(255) NOT NULL,
                    descripcion TEXT,
                    estado VARCHAR(20) DEFAULT 'activo',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Tabla de usuarios
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    nombre VARCHAR(255) NOT NULL,
                    estado VARCHAR(20) DEFAULT 'activo',
                    grupo_id INTEGER REFERENCES grupos(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Tabla intermedia: permisos de grupos sobre reportes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS grupos_reportes (
                    id SERIAL PRIMARY KEY,
                    grupo_id INTEGER NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
                    reporte_codigo VARCHAR(100) NOT NULL,
                    puede_ver BOOLEAN DEFAULT TRUE,
                    puede_crear BOOLEAN DEFAULT FALSE,
                    puede_editar BOOLEAN DEFAULT FALSE,
                    puede_eliminar BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(grupo_id, reporte_codigo)
                );
            ''')
            
            # Insertar grupos por defecto
            cur.execute('''
                INSERT INTO grupos (codigo, nombre, descripcion, estado)
                VALUES ('admin', 'Administradores', 'Grupo con acceso total al sistema', 'activo')
                ON CONFLICT (codigo) DO NOTHING;
            ''')
            
            cur.execute('''
                INSERT INTO grupos (codigo, nombre, descripcion, estado)
                VALUES ('usuarios', 'Usuarios Generales', 'Grupo con permisos básicos de visualización', 'activo')
                ON CONFLICT (codigo) DO NOTHING;
            ''')
            
            # Obtener ID del grupo admin
            cur.execute("SELECT id FROM grupos WHERE codigo = 'admin'")
            grupo_admin_id = cur.fetchone()[0]
            
            # Insertar usuario admin por defecto (password: admin123)
            # Hash simple para demo - en producción usar bcrypt
            cur.execute('''
                INSERT INTO usuarios (username, password, nombre, estado, grupo_id)
                VALUES ('admin', 'admin123', 'Administrador del Sistema', 'activo', %s)
                ON CONFLICT (username) DO NOTHING;
            ''', (grupo_admin_id,))
            
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
                (nombre, codigo, descripcion, contexto, categoria, icono, campos, relaciones, 
                 api_endpoint, query_template, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                reporte_config.api_endpoint if hasattr(reporte_config, 'api_endpoint') else None,
                reporte_config.query_template if hasattr(reporte_config, 'query_template') else None,
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

    def obtener_reporte_admin(self, codigo: str) -> Optional[Dict]:
        """Obtener configuración de un reporte sin filtrar por estado (uso admin)."""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute('''
                SELECT * FROM reportes_config 
                WHERE codigo = %s
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
            if 'activo' in datos:
                campos_update.append('activo = %s')
                valores.append(datos['activo'])
            
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
            errores = []
            
            for idx, datos in enumerate(datos_lista):
                try:
                    # Limpiar datos None y convertir a tipos compatibles con JSON
                    datos_limpios = {}
                    for key, value in datos.items():
                        if pd.isna(value):
                            datos_limpios[key] = None
                        elif isinstance(value, (pd.Timestamp, datetime)):
                            datos_limpios[key] = value.isoformat()
                        else:
                            datos_limpios[key] = value
                    
                    cur.execute('''
                        INSERT INTO datos_reportes (reporte_codigo, datos, uploaded_by)
                        VALUES (%s, %s, %s)
                    ''', (reporte_codigo, json.dumps(datos_limpios), usuario))
                    registros_ok += 1
                except Exception as e:
                    logger.error(f"Error insertando registro {idx + 1}: {e}")
                    errores.append(f"Registro {idx + 1}: {str(e)}")
                    registros_error += 1
                    # Rollback solo este registro para no abortar la transacción completa
                    conn.rollback()
                    # Crear nueva transacción
                    cur = conn.cursor()
            
            conn.commit()
            logger.info(f"Insertados {registros_ok} registros en '{reporte_codigo}'")
            
            return {
                'registros_insertados': registros_ok,
                'registros_error': registros_error,
                'errores': errores[:10] if errores else []  # Solo primeros 10 errores
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
    
    def consultar_datos_filtrado(self, reporte_codigo: str, fecha_inicio=None, fecha_fin=None, 
                                 limite=100, filtros: Optional[Dict] = None):
        """Consultar datos con filtros dinámicos"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            query = '''
                SELECT id, datos, created_at, uploaded_by 
                FROM datos_reportes 
                WHERE reporte_codigo = %s
            '''
            params = [reporte_codigo]
            
            # Filtrar por fecha si se proporciona
            if fecha_inicio:
                query += " AND datos->>'fecha' >= %s"
                params.append(fecha_inicio)
            
            if fecha_fin:
                query += " AND datos->>'fecha' <= %s"
                params.append(fecha_fin)
            
            # Filtros personalizados en campos JSONB
            if filtros:
                for campo, valor in filtros.items():
                    query += f" AND datos->>%s = %s"
                    params.extend([campo, valor])
            
            query += ' ORDER BY created_at DESC LIMIT %s'
            params.append(limite)
            
            cur.execute(query, params)
            
            resultados = []
            for row in cur.fetchall():
                resultado = dict(row)
                resultado['datos'] = row['datos']
                resultados.append(resultado)
            
            return resultados
            
        finally:
            cur.close()
            conn.close()
    
    def consultar_datos_custom(self, reporte_codigo: str, query_template: str, **kwargs):
        """Ejecutar consulta personalizada con template"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Reemplazar placeholders en el template
            query = query_template.format(
                codigo=reporte_codigo,
                **kwargs
            )
            
            cur.execute(query)
            
            resultados = []
            for row in cur.fetchall():
                resultado = dict(row)
                if 'datos' in resultado and isinstance(resultado['datos'], str):
                    import json
                    resultado['datos'] = json.loads(resultado['datos'])
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
    
    # ============================================
    # GESTIÓN DE USUARIOS Y AUTENTICACIÓN
    # ============================================
    
    def autenticar_usuario(self, username: str, password: str) -> Optional[Dict]:
        """Autenticar usuario y devolver sus datos con información del grupo"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute('''
                SELECT u.id, u.username, u.nombre, u.estado, u.grupo_id,
                       g.codigo as grupo_codigo, g.nombre as grupo_nombre
                FROM usuarios u
                LEFT JOIN grupos g ON u.grupo_id = g.id
                WHERE u.username = %s AND u.password = %s AND u.estado = 'activo'
            ''', (username, password))
            
            result = cur.fetchone()
            return dict(result) if result else None
            
        finally:
            cur.close()
            conn.close()
    
    def crear_usuario(self, username: str, password: str, nombre: str, grupo_id: int, estado='activo') -> int:
        """Crear nuevo usuario"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                INSERT INTO usuarios (username, password, nombre, estado, grupo_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (username, password, nombre, estado, grupo_id))
            
            user_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"Usuario '{username}' creado con ID {user_id}")
            return user_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando usuario: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def obtener_usuarios(self) -> List[Dict]:
        """Obtener todos los usuarios"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute('''
                SELECT u.id, u.username, u.nombre, u.estado, u.grupo_id,
                       g.codigo as grupo_codigo, g.nombre as grupo_nombre,
                       u.created_at
                FROM usuarios u
                LEFT JOIN grupos g ON u.grupo_id = g.id
                ORDER BY u.created_at DESC
            ''')
            
            return [dict(row) for row in cur.fetchall()]
            
        finally:
            cur.close()
            conn.close()
    
    def actualizar_usuario(self, user_id: int, datos: Dict) -> bool:
        """Actualizar datos de un usuario"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            updates = []
            params = []
            
            if 'nombre' in datos:
                updates.append('nombre = %s')
                params.append(datos['nombre'])
            if 'estado' in datos:
                updates.append('estado = %s')
                params.append(datos['estado'])
            if 'grupo_id' in datos:
                updates.append('grupo_id = %s')
                params.append(datos['grupo_id'])
            if 'password' in datos:
                updates.append('password = %s')
                params.append(datos['password'])
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(user_id)
            
            query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = %s"
            cur.execute(query, params)
            conn.commit()
            
            return cur.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error actualizando usuario: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    # ============================================
    # GESTIÓN DE GRUPOS
    # ============================================
    
    def crear_grupo(self, codigo: str, nombre: str, descripcion: str = '', estado='activo') -> int:
        """Crear nuevo grupo"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                INSERT INTO grupos (codigo, nombre, descripcion, estado)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (codigo, nombre, descripcion, estado))
            
            grupo_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"Grupo '{nombre}' creado con ID {grupo_id}")
            return grupo_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando grupo: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def obtener_grupos(self) -> List[Dict]:
        """Obtener todos los grupos"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute('''
                SELECT g.*, COUNT(u.id) as total_usuarios
                FROM grupos g
                LEFT JOIN usuarios u ON g.id = u.grupo_id
                GROUP BY g.id
                ORDER BY g.created_at DESC
            ''')
            
            return [dict(row) for row in cur.fetchall()]
            
        finally:
            cur.close()
            conn.close()
    
    def actualizar_grupo(self, grupo_id: int, datos: Dict) -> bool:
        """Actualizar datos de un grupo"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            updates = []
            params = []
            
            if 'nombre' in datos:
                updates.append('nombre = %s')
                params.append(datos['nombre'])
            if 'descripcion' in datos:
                updates.append('descripcion = %s')
                params.append(datos['descripcion'])
            if 'estado' in datos:
                updates.append('estado = %s')
                params.append(datos['estado'])
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(grupo_id)
            
            query = f"UPDATE grupos SET {', '.join(updates)} WHERE id = %s"
            cur.execute(query, params)
            conn.commit()
            
            return cur.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error actualizando grupo: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    # ============================================
    # GESTIÓN DE PERMISOS
    # ============================================
    
    def asignar_permiso_grupo(self, grupo_id: int, reporte_codigo: str, 
                             puede_ver=True, puede_crear=False, 
                             puede_editar=False, puede_eliminar=False) -> int:
        """Asignar permisos de un reporte a un grupo"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                INSERT INTO grupos_reportes 
                (grupo_id, reporte_codigo, puede_ver, puede_crear, puede_editar, puede_eliminar)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (grupo_id, reporte_codigo) 
                DO UPDATE SET 
                    puede_ver = EXCLUDED.puede_ver,
                    puede_crear = EXCLUDED.puede_crear,
                    puede_editar = EXCLUDED.puede_editar,
                    puede_eliminar = EXCLUDED.puede_eliminar
                RETURNING id
            ''', (grupo_id, reporte_codigo, puede_ver, puede_crear, puede_editar, puede_eliminar))
            
            permiso_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"Permiso asignado: grupo {grupo_id} -> reporte {reporte_codigo}")
            return permiso_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error asignando permiso: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def obtener_permisos_grupo(self, grupo_id: int) -> List[Dict]:
        """Obtener todos los permisos de un grupo"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute('''
                SELECT gr.*, rc.nombre as reporte_nombre
                FROM grupos_reportes gr
                LEFT JOIN reportes_config rc ON gr.reporte_codigo = rc.codigo
                WHERE gr.grupo_id = %s
                ORDER BY rc.nombre
            ''', (grupo_id,))
            
            return [dict(row) for row in cur.fetchall()]
            
        finally:
            cur.close()
            conn.close()
    
    def obtener_reportes_permitidos_usuario(self, user_id: int) -> List[str]:
        """Obtener códigos de reportes que un usuario puede ver"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                SELECT DISTINCT gr.reporte_codigo
                FROM grupos_reportes gr
                INNER JOIN usuarios u ON u.grupo_id = gr.grupo_id
                WHERE u.id = %s AND gr.puede_ver = TRUE AND u.estado = 'activo'
            ''', (user_id,))
            
            return [row[0] for row in cur.fetchall()]
            
        finally:
            cur.close()
            conn.close()
    
    def verificar_permiso_usuario(self, user_id: int, reporte_codigo: str, accion='ver') -> bool:
        """Verificar si un usuario tiene permiso para realizar una acción sobre un reporte"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            campo_permiso = {
                'ver': 'puede_ver',
                'crear': 'puede_crear',
                'editar': 'puede_editar',
                'eliminar': 'puede_eliminar'
            }.get(accion, 'puede_ver')
            
            query = f'''
                SELECT gr.{campo_permiso}
                FROM grupos_reportes gr
                INNER JOIN usuarios u ON u.grupo_id = gr.grupo_id
                WHERE u.id = %s AND gr.reporte_codigo = %s AND u.estado = 'activo'
            '''
            
            cur.execute(query, (user_id, reporte_codigo))
            result = cur.fetchone()
            
            return result[0] if result else False
            
        finally:
            cur.close()
            conn.close()
    
    def eliminar_permiso_grupo(self, grupo_id: int, reporte_codigo: str) -> bool:
        """Eliminar permiso de un grupo sobre un reporte"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                DELETE FROM grupos_reportes 
                WHERE grupo_id = %s AND reporte_codigo = %s
            ''', (grupo_id, reporte_codigo))
            
            conn.commit()
            return cur.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error eliminando permiso: {e}")
            raise
        finally:
            cur.close()
            conn.close()    
    # ============================================
    # MÉTODOS PARA CONTROL DE PERIODOS
    # ============================================
    
    def crear_reporte_config(
        self,
        nombre: str,
        codigo: str,
        descripcion: str,
        campos: List[Dict],
        categoria: str = 'general',
        tipo_periodo: str = 'libre',
        campo_fecha: str = None,
        requiere_periodo: bool = False,
        validacion_ia: Dict = None
    ) -> Dict:
        """
        Crear nuevo reporte con configuración de periodo
        """
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute('''
                INSERT INTO reportes_config 
                (nombre, codigo, descripcion, campos, categoria, 
                 tipo_periodo, campo_fecha, requiere_periodo, validacion_ia, estado_validacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', (
                nombre, codigo, descripcion, json.dumps(campos), categoria,
                tipo_periodo, campo_fecha, requiere_periodo, 
                json.dumps(validacion_ia) if validacion_ia else None,
                'validado' if validacion_ia and validacion_ia.get('valido') else 'pendiente'
            ))
            
            result = cur.fetchone()
            conn.commit()
            
            return dict(result) if result else None
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando reporte_config: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def obtener_reporte_por_codigo(self, codigo: str) -> Optional[Dict]:
        """
        Obtener configuración de reporte por código
        """
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute('''
                SELECT * FROM reportes_config 
                WHERE codigo = %s
            ''', (codigo,))
            
            result = cur.fetchone()
            return dict(result) if result else None
            
        finally:
            cur.close()
            conn.close()
    
    def ejecutar_query(self, query: str, params: tuple = None, commit: bool = False):
        """
        Ejecutar query SQL personalizada
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            
            # Si es SELECT, devolver resultados
            if query.strip().upper().startswith('SELECT') or 'RETURNING' in query.upper():
                results = cur.fetchall()
            else:
                results = None
            
            if commit:
                conn.commit()
            
            return results
            
        except Exception as e:
            if commit:
                conn.rollback()
            logger.error(f"Error ejecutando query: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def commit(self):
        """
        Commit para transacciones múltiples
        Nota: Este método necesita refactor para manejar conexiones persistentes
        """
        # Por ahora, el commit se maneja en ejecutar_query con commit=True
        pass