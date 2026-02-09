"""
Módulo de gestión de aclaraciones y validaciones de IA
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
import psycopg2.extras

logger = logging.getLogger(__name__)

class AclaracionesManager:
    """Gestor de aclaraciones de campos y validaciones de IA"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    # ==================== ACLARACIONES DE CAMPOS ====================
    
    def crear_aclaracion(self, reporte_codigo: str, nombre_campo: str, pregunta_ia: str, contexto: str = None) -> int:
        """Crear una nueva aclaración para un campo"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                INSERT INTO campo_aclaraciones 
                (reporte_codigo, nombre_campo, pregunta_ia, estado, contexto_uso)
                VALUES (%s, %s, %s, 'pendiente', %s)
                ON CONFLICT (reporte_codigo, nombre_campo) 
                DO UPDATE SET 
                    pregunta_ia = EXCLUDED.pregunta_ia,
                    estado = 'pendiente',
                    contexto_uso = EXCLUDED.contexto_uso,
                    fecha_pregunta = CURRENT_TIMESTAMP
                RETURNING id
            ''', (reporte_codigo, nombre_campo, pregunta_ia, contexto))
            
            aclaracion_id = cur.fetchone()[0]
            conn.commit()
            
            # Crear notificación para usuarios
            self._crear_notificacion_aclaracion_requerida(reporte_codigo, nombre_campo, pregunta_ia)
            
            logger.info(f"Aclaración creada para campo {nombre_campo} en {reporte_codigo}")
            return aclaracion_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando aclaración: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def obtener_aclaraciones_pendientes(self, reporte_codigo: str = None) -> List[Dict]:
        """Obtener aclaraciones pendientes de respuesta"""
        conn = self.db.get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            query = '''
                SELECT id, reporte_codigo, nombre_campo, pregunta_ia, estado,
                       fecha_pregunta, contexto_uso, respuesta_usuario,
                       fecha_respuesta_usuario, usuario_respondio
                FROM campo_aclaraciones
                WHERE estado IN ('pendiente', 'respondida_usuario')
            '''
            params = []
            
            if reporte_codigo:
                query += ' AND reporte_codigo = %s'
                params.append(reporte_codigo)
            
            query += ' ORDER BY fecha_pregunta DESC'
            
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
            
        finally:
            cur.close()
            conn.close()
    
    def responder_aclaracion_usuario(self, aclaracion_id: int, respuesta: str, usuario: str) -> bool:
        """Usuario responde la aclaración de un campo"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                UPDATE campo_aclaraciones
                SET respuesta_usuario = %s,
                    usuario_respondio = %s,
                    fecha_respuesta_usuario = CURRENT_TIMESTAMP,
                    estado = 'respondida_usuario'
                WHERE id = %s
                RETURNING reporte_codigo, nombre_campo, pregunta_ia
            ''', (respuesta, usuario, aclaracion_id))
            
            row = cur.fetchone()
            conn.commit()
            
            if row:
                # Crear notificación para admin
                self._crear_notificacion_respuesta_usuario(aclaracion_id, row[0], row[1], respuesta, usuario)
                logger.info(f"Usuario {usuario} respondió aclaración {aclaracion_id}")
                return True
            
            return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error respondiendo aclaración: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def validar_aclaracion_admin(self, aclaracion_id: int, respuesta_final: str, admin: str, aprobar: bool = True) -> bool:
        """Admin valida y aprueba/mejora la respuesta del usuario"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                UPDATE campo_aclaraciones
                SET respuesta_admin = %s,
                    admin_respondio = %s,
                    fecha_respuesta_admin = CURRENT_TIMESTAMP,
                    aprobado = %s,
                    fecha_aprobacion = CURRENT_TIMESTAMP,
                    estado = 'aprobada'
                WHERE id = %s
                RETURNING reporte_codigo, nombre_campo
            ''', (respuesta_final, admin, aprobar, aclaracion_id))
            
            row = cur.fetchone()
            conn.commit()
            
            if row:
                # Guardar en base de conocimiento de IA
                self._agregar_a_base_conocimiento(row[0], row[1], respuesta_final)
                logger.info(f"Admin {admin} validó aclaración {aclaracion_id}")
                return True
            
            return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error validando aclaración: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def obtener_aclaraciones_aprobadas(self, reporte_codigo: str) -> Dict[str, str]:
        """Obtener diccionario de aclaraciones aprobadas para un reporte"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                SELECT nombre_campo, respuesta_admin
                FROM campo_aclaraciones
                WHERE reporte_codigo = %s AND aprobado = TRUE
            ''', (reporte_codigo,))
            
            return {row[0]: row[1] for row in cur.fetchall()}
            
        finally:
            cur.close()
            conn.close()
    
    # ==================== VALIDACIONES DE REPORTES ====================
    
    def guardar_validacion_reporte(self, reporte_codigo: str, resultado: Dict, validador: str = 'gpt-4o') -> int:
        """Guardar resultado de validación de reporte por IA"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        try:
            import json
            
            cur.execute('''
                INSERT INTO reporte_validaciones_ia 
                (reporte_codigo, validador_ia, resultado, campos_dudosos, sugerencias, 
                 puntuacion_claridad, aprobado_por_ia, validado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                reporte_codigo,
                validador,
                json.dumps(resultado),
                json.dumps(resultado.get('campos_dudosos', [])),
                json.dumps(resultado.get('sugerencias', [])),
                resultado.get('puntuacion_claridad', 0),
                resultado.get('aprobado', True),
                'system'
            ))
            
            validacion_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"Validación de reporte {reporte_codigo} guardada con ID {validacion_id}")
            return validacion_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error guardando validación: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    # ==================== NOTIFICACIONES ====================
    
    def crear_notificacion(self, tipo: str, titulo: str, mensaje: str, datos: Dict = None, 
                          relacionado_con: str = None, relacionado_id: int = None) -> int:
        """Crear notificación para administradores"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        try:
            import json
            
            cur.execute('''
                INSERT INTO notificaciones_admin 
                (tipo, titulo, mensaje, datos, relacionado_con, relacionado_id, leido)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                RETURNING id
            ''', (tipo, titulo, mensaje, json.dumps(datos) if datos else None, 
                  relacionado_con, relacionado_id))
            
            notif_id = cur.fetchone()[0]
            conn.commit()
            
            return notif_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando notificación: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def obtener_notificaciones_no_leidas(self, admin_usuario: str = None) -> List[Dict]:
        """Obtener notificaciones no leídas"""
        conn = self.db.get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            query = '''
                SELECT id, tipo, titulo, mensaje, datos, relacionado_con, relacionado_id,
                       fecha_creacion
                FROM notificaciones_admin
                WHERE leido = FALSE
            '''
            params = []
            
            if admin_usuario:
                query += ' AND (admin_usuario IS NULL OR admin_usuario = %s)'
                params.append(admin_usuario)
            
            query += ' ORDER BY fecha_creacion DESC LIMIT 50'
            
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
            
        finally:
            cur.close()
            conn.close()
    
    def marcar_notificacion_leida(self, notificacion_id: int) -> bool:
        """Marcar notificación como leída"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                UPDATE notificaciones_admin
                SET leido = TRUE, fecha_leido = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (notificacion_id,))
            
            conn.commit()
            return cur.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error marcando notificación: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    
    # ==================== MÉTODOS PRIVADOS ====================
    
    def _crear_notificacion_aclaracion_requerida(self, reporte_codigo: str, campo: str, pregunta: str):
        """Crear notificación cuando se requiere aclaración"""
        self.crear_notificacion(
            tipo='aclaracion_requerida',
            titulo=f'Aclaración requerida en {reporte_codigo}',
            mensaje=f'La IA necesita aclaración sobre el campo "{campo}": {pregunta}',
            datos={'reporte': reporte_codigo, 'campo': campo, 'pregunta': pregunta}
        )
    
    def _crear_notificacion_respuesta_usuario(self, aclaracion_id: int, reporte: str, campo: str, respuesta: str, usuario: str):
        """Crear notificación cuando usuario responde"""
        self.crear_notificacion(
            tipo='respuesta_usuario',
            titulo=f'Usuario respondió aclaración en {reporte}',
            mensaje=f'Usuario {usuario} explicó el campo "{campo}". Requiere validación.',
            datos={'campo': campo, 'respuesta': respuesta, 'usuario': usuario},
            relacionado_con='aclaracion',
            relacionado_id=aclaracion_id
        )
    
    def _agregar_a_base_conocimiento(self, reporte: str, campo: str, respuesta: str):
        """Agregar aclaración aprobada a base de conocimiento de IA"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        try:
            import json
            
            cur.execute('''
                INSERT INTO ia_aprendizaje 
                (tipo_aprendizaje, contexto, respuesta_mejorada, fuente, tags, activo)
                VALUES ('aclaracion_campo', %s, %s, 'admin_validation', %s, TRUE)
            ''', (
                f"Campo '{campo}' en reporte '{reporte}'",
                respuesta,
                json.dumps({'reporte': reporte, 'campo': campo, 'tipo': 'aclaracion'})
            ))
            
            conn.commit()
            logger.info(f"Aclaración agregada a base de conocimiento: {reporte}/{campo}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error agregando a base de conocimiento: {e}")
        finally:
            cur.close()
            conn.close()
