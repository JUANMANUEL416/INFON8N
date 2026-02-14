from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import pandas as pd
from io import BytesIO
from datetime import datetime
import json
from flask_mail import Mail, Message
import base64

from db_manager import DatabaseManager
import threading
from models import ReporteConfig, CampoConfig, RelacionConfig
from analysis_agent import DataAnalysisAgent
from aclaraciones_manager import AclaracionesManager

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@sistema.com')

mail = Mail(app)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de base de datos
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': os.getenv('DB_PORT', 5432),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123'),
    'database': os.getenv('DB_NAME', 'informes_db')
}

# Inicializar Database Manager
db_manager = DatabaseManager(DB_CONFIG)

# Inicializar agente de análisis
analysis_agent = DataAnalysisAgent(db_manager, openai_api_key=os.getenv('OPENAI_API_KEY'))

# Inicializar gestor de aclaraciones
aclaraciones_manager = AclaracionesManager(db_manager)

# ============================================
# RUTAS PÚBLICAS
# ============================================

@app.route('/login', methods=['GET'])
def login_page():
    """Página de login"""
    return render_template('login.html')

@app.route('/', methods=['GET'])
def index():
    """Página principal - Portal de Usuario"""
    return render_template('usuario.html')

@app.route('/admin', methods=['GET'])
def admin():
    """Panel de Administración"""
    return render_template('admin.html')

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de salud"""
    try:
        conn = db_manager.get_connection()
        conn.close()
        return jsonify({'status': 'ok', 'message': 'Sistema funcionando'}), 200
    except:
        return jsonify({'status': 'error', 'message': 'BD no disponible'}), 500

# ============================================
# API - ADMINISTRADOR
# ============================================

# Endpoint público para listar reportes activos (para el uso general del frontend)
@app.route('/api/reportes', methods=['GET', 'OPTIONS'])
def listar_reportes_publico():
    """Listar reportes activos. Incluye OPTIONS para que el preflight CORS no falle."""
    try:
        if request.method == 'OPTIONS':
            # Responder OK al preflight
            return '', 200
        reportes = db_manager.listar_reportes(solo_activos=True)
        return jsonify(reportes), 200
    except Exception as e:
        logger.error(f"Error listando reportes públicos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reportes', methods=['GET'])
def listar_reportes():
    """Listar todos los reportes (incluyendo inactivos)"""
    try:
        reportes = db_manager.listar_reportes(solo_activos=False)
        return jsonify(reportes), 200
    except Exception as e:
        logger.error(f"Error listando reportes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reportes', methods=['POST'])
def crear_reporte():
    """Crear nuevo reporte con validación IA"""
    try:
        datos = request.json
        
        # Validar campos obligatorios
        if not datos.get('nombre') or not datos.get('codigo'):
            return jsonify({'error': 'Nombre y código son obligatorios'}), 400
        
        # Validar que se envíe listado de campos
        campos = datos.get('campos')
        if not campos or not isinstance(campos, list) or len(campos) == 0:
            return jsonify({'error': 'Debe especificar el listado de campos del reporte'}), 400
        
        # Validar estructura mínima de cada campo
        errores_campos = []
        for i, c in enumerate(campos, start=1):
            if not isinstance(c, dict):
                errores_campos.append(f"Campo #{i} no es un objeto válido")
                continue
            if not c.get('nombre'):
                errores_campos.append(f"Campo #{i} sin 'nombre'")
            if not c.get('tipo') and not c.get('tipo_dato'):
                errores_campos.append(f"Campo '{c.get('nombre','(sin nombre)')}' sin 'tipo' o 'tipo_dato'")
            # Normalizar flags
            if 'obligatorio' not in c:
                c['obligatorio'] = False
        if errores_campos:
            return jsonify({'error': 'Errores en definición de campos', 'detalles': errores_campos}), 400
        
        # Validar con IA si está habilitado
        validacion_ia = None
        if datos.get('campos') and os.getenv('ENABLE_IA_VALIDATION', 'true').lower() == 'true':
            try:
                validacion_ia = analysis_agent.validar_reporte_con_ia(datos['campos'])
                
                # Guardar resultado de validación
                aclaraciones_manager.guardar_validacion_reporte(
                    datos['codigo'],
                    validacion_ia
                )
                
                # Si hay campos dudosos, crear aclaraciones
                if validacion_ia.get('campos_dudosos'):
                    for campo_dudoso in validacion_ia['campos_dudosos']:
                        if campo_dudoso.get('severidad') in ['alta', 'media']:
                            # Generar pregunta de aclaración
                            pregunta = analysis_agent.generar_pregunta_aclaracion(
                                campo_dudoso['nombre'],
                                next((c['tipo'] for c in datos['campos'] if c['nombre'] == campo_dudoso['nombre']), 'texto'),
                                next((c.get('descripcion', '') for c in datos['campos'] if c['nombre'] == campo_dudoso['nombre']), ''),
                                campo_dudoso['razon']
                            )
                            
                            # Crear registro de aclaración
                            aclaraciones_manager.crear_aclaracion(
                                datos['codigo'],
                                campo_dudoso['nombre'],
                                pregunta,
                                json.dumps(campo_dudoso)
                            )
                
                logger.info(f"Validación IA completada para {datos['codigo']}: {validacion_ia.get('puntuacion_claridad', 0)}/100")
                
            except Exception as e:
                logger.error(f"Error en validación IA (continuando sin validación): {e}")
                validacion_ia = None
        
        # Crear configuración
        reporte = ReporteConfig(datos)
        
        # Guardar en BD
        reporte_id = db_manager.crear_reporte(reporte)
        
        respuesta = {
            'success': True,
            'reporte_id': reporte_id,
            'message': f"Reporte '{datos['nombre']}' creado correctamente"
        }
        
        # Agregar información de validación si existe
        if validacion_ia:
            tiene_dudas = len(validacion_ia.get('campos_dudosos', [])) > 0
            respuesta['validacion_ia'] = {
                'puntuacion': validacion_ia.get('puntuacion_claridad', 0),
                'campos_con_dudas': len(validacion_ia.get('campos_dudosos', [])),
                'requiere_aclaraciones': tiene_dudas,
                'estado_validacion': 'pendiente' if tiene_dudas else 'validado'
            }
            # Si hay dudas, desactivar el reporte hasta que se resuelva
            if tiene_dudas:
                try:
                    db_manager.actualizar_reporte(datos['codigo'], {'activo': False})
                    respuesta['reporte_desactivado'] = True
                    respuesta['message'] += " (Creado inactivo: requiere aclaraciones de campos)"
                except Exception as e_upd:
                    logger.warning(f"No se pudo desactivar reporte con dudas: {e_upd}")
        
        return jsonify(respuesta), 201
        
    except Exception as e:
        logger.error(f"Error creando reporte: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reportes/<codigo>', methods=['GET'])
def obtener_reporte(codigo):
    """Obtener configuración de un reporte"""
    try:
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        return jsonify(reporte), 200
    except Exception as e:
        logger.error(f"Error obteniendo reporte: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reportes/<codigo>', methods=['PUT'])
def actualizar_reporte(codigo):
    """Actualizar configuración de reporte"""
    try:
        datos = request.json
        success = db_manager.actualizar_reporte(codigo, datos)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Reporte '{codigo}' actualizado"
            }), 200
        else:
            return jsonify({'error': 'Error al actualizar'}), 500
            
    except Exception as e:
        logger.error(f"Error actualizando reporte: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reportes/<codigo>', methods=['DELETE'])
def eliminar_reporte(codigo):
    """Desactivar un reporte"""
    try:
        success = db_manager.actualizar_reporte(codigo, {'activo': False})
        if success:
            return jsonify({
                'success': True,
                'message': f"Reporte '{codigo}' desactivado"
            }), 200
        else:
            return jsonify({'error': 'Error al desactivar'}), 500
    except Exception as e:
        logger.error(f"Error eliminando reporte: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# API - SISTEMA DE ACLARACIONES Y VALIDACIONES IA
# ============================================

# ============================================
# API - ADMIN: GESTIÓN DE CAMPOS DE REPORTE
# ============================================

@app.route('/api/admin/reportes/<codigo>/campos', methods=['GET'])
def admin_listar_campos(codigo):
    """Listar campos del reporte para administración."""
    try:
        reporte = db_manager.obtener_reporte_admin(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        campos = reporte.get('campos') or []
        if isinstance(campos, str):
            try:
                campos = json.loads(campos)
            except Exception:
                campos = []
        return jsonify({'campos': campos, 'total': len(campos)}), 200
    except Exception as e:
        logger.error(f"Error listando campos admin: {e}")
        return jsonify({'error': str(e)}), 500

def _validar_campos_definicion(campos: list):
    """Validar estructura mínima de campos."""
    errores = []
    for i, c in enumerate(campos, start=1):
        if not isinstance(c, dict):
            errores.append(f"Campo #{i} no es un objeto válido")
            continue
        if not c.get('nombre'):
            errores.append(f"Campo #{i} sin 'nombre'")
        if not c.get('tipo') and not c.get('tipo_dato'):
            errores.append(f"Campo '{c.get('nombre','(sin nombre)')}' sin 'tipo' o 'tipo_dato'")
        if 'obligatorio' not in c:
            c['obligatorio'] = False
    return errores

def _post_validacion_ia_campos(codigo: str, campos: list):
    """Ejecutar validación IA y crear aclaraciones si hay dudas. Posible desactivación."""
    try:
        validacion_ia = analysis_agent.validar_reporte_con_ia(campos)
        aclaraciones_manager.guardar_validacion_reporte(codigo, validacion_ia)
        if validacion_ia.get('campos_dudosos'):
            for campo_dudoso in validacion_ia['campos_dudosos']:
                if campo_dudoso.get('severidad') in ['alta', 'media']:
                    pregunta = analysis_agent.generar_pregunta_aclaracion(
                        campo_dudoso.get('nombre'),
                        campo_dudoso.get('tipo', 'texto'),
                        campo_dudoso.get('descripcion', ''),
                        campo_dudoso.get('razon', '')
                    )
                    aclaraciones_manager.crear_aclaracion(
                        codigo,
                        campo_dudoso.get('nombre'),
                        pregunta,
                        json.dumps(campo_dudoso)
                    )
            # Desactivar reporte hasta resolución
            db_manager.actualizar_reporte(codigo, {'activo': False})
            return {'requiere_aclaraciones': True, 'estado_validacion': 'pendiente'}
        return {'requiere_aclaraciones': False, 'estado_validacion': 'validado'}
    except Exception as e:
        logger.warning(f"Validación IA de campos falló: {e}")
        return {'requiere_aclaraciones': False, 'estado_validacion': 'sin-validar'}

@app.route('/api/admin/reportes/<codigo>/campos', methods=['PUT'])
def admin_actualizar_campos(codigo):
    """Actualizar listado completo de campos de un reporte."""
    try:
        datos = request.json or {}
        campos = datos.get('campos')
        if not campos or not isinstance(campos, list) or len(campos) == 0:
            return jsonify({'error': 'Debe especificar el listado de campos del reporte'}), 400
        errores = _validar_campos_definicion(campos)
        if errores:
            return jsonify({'error': 'Errores en definición de campos', 'detalles': errores}), 400
        ok = db_manager.actualizar_reporte(codigo, {'campos': campos})
        if not ok:
            return jsonify({'error': 'No se pudo actualizar el reporte'}), 500
        post = _post_validacion_ia_campos(codigo, campos)
        return jsonify({'success': True, 'message': 'Campos actualizados', **post}), 200
    except Exception as e:
        logger.error(f"Error actualizando campos admin: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reportes/<codigo>/campos', methods=['POST'])
def admin_agregar_campo(codigo):
    """Agregar un campo al reporte (evita duplicados por nombre)."""
    try:
        datos = request.json or {}
        campo = datos.get('campo')
        if not campo or not isinstance(campo, dict):
            return jsonify({'error': 'Debe enviar objeto "campo" válido'}), 400
        campos_exist = db_manager.obtener_reporte_admin(codigo)
        if not campos_exist:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        campos = campos_exist.get('campos') or []
        if isinstance(campos, str):
            try:
                campos = json.loads(campos)
            except Exception:
                campos = []
        # Validar nuevo campo en conjunto
        nuevos_campos = [c for c in campos if c.get('nombre') != campo.get('nombre')]
        nuevos_campos.append(campo)
        errores = _validar_campos_definicion(nuevos_campos)
        if errores:
            return jsonify({'error': 'Errores en definición de campos', 'detalles': errores}), 400
        ok = db_manager.actualizar_reporte(codigo, {'campos': nuevos_campos})
        if not ok:
            return jsonify({'error': 'No se pudo actualizar el reporte'}), 500
        post = _post_validacion_ia_campos(codigo, nuevos_campos)
        return jsonify({'success': True, 'message': 'Campo agregado', **post}), 200
    except Exception as e:
        logger.error(f"Error agregando campo admin: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reportes/<codigo>/campos/<nombre>/aclaracion', methods=['POST'])
def admin_crear_aclaracion_campo(codigo, nombre):
    """Generar una aclaración para un campo específico del reporte."""
    try:
        datos = request.json or {}
        descripcion = datos.get('descripcion', '')
        tipo = datos.get('tipo', 'texto')
        razon = datos.get('razon', 'Necesita aclaración por parte del administrador')
        pregunta = analysis_agent.generar_pregunta_aclaracion(nombre, tipo, descripcion, razon)
        aclaraciones_manager.crear_aclaracion(codigo, nombre, pregunta, json.dumps({'tipo': tipo, 'razon': razon}))
        return jsonify({'success': True, 'pregunta': pregunta}), 201
    except Exception as e:
        logger.error(f"Error creando aclaración de campo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/aclaraciones/<reporte_codigo>', methods=['GET'])
def obtener_aclaraciones(reporte_codigo):
    """Obtener aclaraciones pendientes para un reporte"""
    try:
        aclaraciones = aclaraciones_manager.obtener_aclaraciones_pendientes(reporte_codigo)
        return jsonify({
            'success': True,
            'aclaraciones': aclaraciones,
            'total': len(aclaraciones)
        }), 200
    except Exception as e:
        logger.error(f"Error obteniendo aclaraciones: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/aclaraciones/<int:aclaracion_id>/responder', methods=['POST'])
def responder_aclaracion(aclaracion_id):
    """Usuario responde una aclaración"""
    try:
        datos = request.json
        
        if not datos.get('respuesta'):
            return jsonify({'error': 'Se requiere una respuesta'}), 400
        
        usuario = datos.get('usuario', 'usuario_anonimo')
        
        success = aclaraciones_manager.responder_aclaracion_usuario(
            aclaracion_id,
            datos['respuesta'],
            usuario
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Respuesta guardada. Un administrador la revisará.'
            }), 200
        else:
            return jsonify({'error': 'Aclaración no encontrada'}), 404
            
    except Exception as e:
        logger.error(f"Error respondiendo aclaración: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/aclaraciones/<int:aclaracion_id>/validar', methods=['POST'])
def validar_aclaracion_admin(aclaracion_id):
    """Admin valida y aprueba/mejora respuesta de usuario"""
    try:
        datos = request.json
        
        if not datos.get('respuesta_final'):
            return jsonify({'error': 'Se requiere respuesta final'}), 400
        
        admin = datos.get('admin', 'admin')
        aprobar = datos.get('aprobar', True)
        
        success = aclaraciones_manager.validar_aclaracion_admin(
            aclaracion_id,
            datos['respuesta_final'],
            admin,
            aprobar
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Aclaración validada y guardada en base de conocimiento'
            }), 200
        else:
            return jsonify({'error': 'Aclaración no encontrada'}), 404
            
    except Exception as e:
        logger.error(f"Error validando aclaración: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/notificaciones', methods=['GET'])
def obtener_notificaciones():
    """Obtener notificaciones no leídas para admin"""
    try:
        admin = request.args.get('admin', None)
        notificaciones = aclaraciones_manager.obtener_notificaciones_no_leidas(admin)
        
        return jsonify({
            'success': True,
            'notificaciones': notificaciones,
            'total': len(notificaciones)
        }), 200
    except Exception as e:
        logger.error(f"Error obteniendo notificaciones: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/notificaciones/<int:notificacion_id>/marcar-leida', methods=['POST'])
def marcar_notificacion_leida(notificacion_id):
    """Marcar notificación como leída"""
    try:
        success = aclaraciones_manager.marcar_notificacion_leida(notificacion_id)
        
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Notificación no encontrada'}), 404
            
    except Exception as e:
        logger.error(f"Error marcando notificación: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/aclaraciones/pendientes', methods=['GET'])
def listar_aclaraciones_pendientes():
    """Listar todas las aclaraciones pendientes de validación admin"""
    try:
        aclaraciones = aclaraciones_manager.obtener_aclaraciones_pendientes()
        
        return jsonify({
            'success': True,
            'aclaraciones': aclaraciones,
            'total': len(aclaraciones)
        }), 200
    except Exception as e:
        logger.error(f"Error listando aclaraciones: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/analizar-excel', methods=['POST'])

def analizar_excel():
    """Analizar archivo Excel y extraer estructura de campos"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': 'Solo archivos .xlsx permitidos'}), 400
        
        # Leer Excel
        df = pd.read_excel(file, nrows=1)  # Solo primera fila de datos
        
        # Inferir tipo de dato
        def inferir_tipo(valor, nombre_columna):
            """Inferir tipo de dato basado en el valor de ejemplo"""
            if pd.isna(valor):
                return 'texto'
            
            # Intentar convertir a diferentes tipos
            valor_str = str(valor).lower()
            
            # Fecha
            try:
                pd.to_datetime(valor)
                return 'fecha'
            except:
                pass
            
            # Número entero
            try:
                if float(valor) == int(float(valor)):
                    return 'numero'
            except:
                pass
            
            # Decimal
            try:
                float(valor)
                return 'decimal'
            except:
                pass
            
            # Email
            if '@' in valor_str and '.' in valor_str:
                return 'email'
            
            # Teléfono
            if valor_str.replace('-', '').replace(' ', '').replace('+', '').isdigit():
                return 'telefono'
            
            # Booleano
            if valor_str in ['si', 'no', 'true', 'false', '1', '0', 'sí']:
                return 'booleano'
            
            # Por defecto texto
            return 'texto'
        
        # Extraer campos
        campos = []
        for idx, columna in enumerate(df.columns):
            valor_ejemplo = df[columna].iloc[0] if len(df) > 0 else None
            
            campo = {
                'nombre': str(columna).lower().replace(' ', '_').replace('ñ', 'n'),
                'etiqueta': str(columna),
                'tipo_dato': inferir_tipo(valor_ejemplo, columna),
                'obligatorio': True if idx < 3 else False,  # Primeros 3 campos obligatorios
                'descripcion': f'Campo {columna}',
                'ejemplo': str(valor_ejemplo) if valor_ejemplo is not None else '',
                'orden': idx
            }
            campos.append(campo)
        
        return jsonify({
            'success': True,
            'campos': campos,
            'total_campos': len(campos),
            'message': f'Se detectaron {len(campos)} campos automáticamente'
        }), 200
        
    except Exception as e:
        logger.error(f"Error analizando Excel: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# API - USUARIO
# ============================================

@app.route('/api/reportes/disponibles', methods=['GET'])
def reportes_disponibles():
    """Listar reportes disponibles para usuarios"""
    try:
        reportes = db_manager.listar_reportes(solo_activos=True)
        
        # Simplificar info para usuario
        reportes_usuario = []
        for r in reportes:
            reportes_usuario.append({
                'codigo': r['codigo'],
                'nombre': r['nombre'],
                'descripcion': r['descripcion'],
                'categoria': r['categoria'],
                'icono': r['icono']
            })
        
        return jsonify(reportes_usuario), 200
    except Exception as e:
        logger.error(f"Error listando reportes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/<codigo>/descargar', methods=['GET'])
def descargar_plantilla(codigo):
    """Descargar plantilla Excel de un reporte"""
    try:
        # Obtener configuración del reporte
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        # Crear Excel con estructura
        campos = reporte.get('campos', [])
        
        # Hoja 1: Datos (vacía)
        columnas = [campo['nombre'] for campo in campos]
        df_datos = pd.DataFrame(columns=columnas)
        
        # Hoja 2: Ejemplo
        ejemplo = {}
        for campo in campos:
            ejemplo[campo['nombre']] = campo.get('ejemplo', '')
        df_ejemplo = pd.DataFrame([ejemplo])
        
        # Hoja 3: Instrucciones
        instrucciones = []
        instrucciones.append({
            'Reporte': reporte['nombre'],
            'Descripción': reporte['descripcion']
        })
        instrucciones.append({'Reporte': '', 'Descripción': ''})
        instrucciones.append({
            'Reporte': 'CONTEXTO',
            'Descripción': reporte.get('contexto', '')
        })
        instrucciones.append({'Reporte': '', 'Descripción': ''})
        instrucciones.append({
            'Reporte': 'CAMPOS',
            'Descripción': 'Descripción'
        })
        
        for campo in campos:
            obligatorio = '✓' if campo.get('obligatorio') else ''
            instrucciones.append({
                'Reporte': f"{campo['etiqueta']} {obligatorio}",
                'Descripción': campo.get('descripcion', '')
            })
        
        df_instrucciones = pd.DataFrame(instrucciones)
        
        # Crear archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_datos.to_excel(writer, sheet_name='Datos', index=False)
            df_ejemplo.to_excel(writer, sheet_name='Ejemplo', index=False)
            df_instrucciones.to_excel(writer, sheet_name='Instrucciones', index=False)
        
        output.seek(0)
        
        filename = f"plantilla_{codigo}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error generando plantilla: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """Endpoint simplificado para subir datos (redirige a /api/reportes/<codigo>/upload)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        if 'type' not in request.form:
            return jsonify({'error': 'No se proporcionó el tipo de reporte'}), 400
        
        codigo = request.form['type']
        file = request.files['file']
        
        # Validar extensión (.xlsx o .xls)
        if not (file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls')):
            return jsonify({'error': 'Solo archivos .xlsx o .xls permitidos'}), 400
        
        # Obtener configuración del reporte
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        # Leer Excel (preferir hoja 'Datos' ignorando mayúsculas/espacios; si no existe usar primera hoja)
        try:
            xls = pd.ExcelFile(file)
            sheet_names = xls.sheet_names
            normalized = [s.strip().lower() for s in sheet_names]
            hoja = sheet_names[normalized.index('datos')] if 'datos' in normalized else sheet_names[0]
            logger.info(f"Hojas del Excel: {sheet_names}. Usando hoja: {hoja}")
            df = xls.parse(sheet_name=hoja)
        except Exception as e:
            logger.warning(f"Fallo leyendo hoja específica, intentando fallback a primera hoja. Error: {e}")
            try:
                # Reiniciar el puntero del archivo y leer la primera hoja
                file.seek(0)
                df = pd.read_excel(file, sheet_name=0)
            except Exception as e2:
                raise e2
        
        # Validar estructura
        campos_config = reporte.get('campos', [])
        if isinstance(campos_config, str):
            try:
                campos_config = json.loads(campos_config)
            except Exception:
                logger.warning("No se pudo parsear campos_config como JSON; usando valor original si es lista")
        
        campos_requeridos = [c['nombre'] for c in campos_config if c.get('obligatorio')]
        campos_excel = df.columns.tolist()
        
        # Verificar campos obligatorios
        faltantes = [c for c in campos_requeridos if c not in campos_excel]
        if faltantes:
            return jsonify({
                'error': f"Faltan campos obligatorios: {', '.join(faltantes)}"
            }), 400
        
        # Convertir a lista de diccionarios
        datos_lista = df.to_dict('records')
        
        # Insertar en BD
        resultado = db_manager.insertar_datos(codigo, datos_lista, usuario='usuario')
        
        return jsonify({
            'success': True,
            'records': resultado['registros_insertados'],
            'file': file.filename,
            'message': f"Se procesaron {resultado['registros_insertados']} registros"
        }), 200
        
    except Exception as e:
        logger.error(f"Error subiendo archivo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/<codigo>/upload', methods=['POST'])
def subir_datos(codigo):
    """Subir datos de un reporte"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        
        # Validar extensión (.xlsx o .xls)
        if not (file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls')):
            return jsonify({'error': 'Solo archivos .xlsx o .xls permitidos'}), 400
        
        # Obtener configuración del reporte
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        # Leer Excel (preferir hoja 'Datos' ignorando mayúsculas/espacios; si no existe usar primera hoja)
        try:
            xls = pd.ExcelFile(file)
            sheet_names = xls.sheet_names
            normalized = [s.strip().lower() for s in sheet_names]
            hoja = sheet_names[normalized.index('datos')] if 'datos' in normalized else sheet_names[0]
            logger.info(f"Hojas del Excel: {sheet_names}. Usando hoja: {hoja}")
            df = xls.parse(sheet_name=hoja)
        except Exception as e:
            logger.warning(f"Fallo leyendo hoja específica, intentando fallback a primera hoja. Error: {e}")
            try:
                file.seek(0)
                df = pd.read_excel(file, sheet_name=0)
            except Exception as e2:
                raise e2
        
        # Validar estructura
        campos_config = reporte.get('campos', [])
        if isinstance(campos_config, str):
            try:
                campos_config = json.loads(campos_config)
            except Exception:
                logger.warning("No se pudo parsear campos_config como JSON en subir_datos; usando valor original si es lista")
        campos_requeridos = [c['nombre'] for c in campos_config if c.get('obligatorio')]
        campos_excel = df.columns.tolist()
        
        # Verificar campos obligatorios
        faltantes = [c for c in campos_requeridos if c not in campos_excel]
        if faltantes:
            return jsonify({
                'error': f"Faltan campos obligatorios: {', '.join(faltantes)}"
            }), 400
        
        # Convertir a lista de diccionarios
        datos_lista = df.to_dict('records')
        
        # Insertar en BD
        resultado = db_manager.insertar_datos(codigo, datos_lista, usuario='usuario')
        
        # Auto-indexar en ChromaDB en segundo plano para evitar bloqueos largos
        try:
            if resultado['registros_insertados'] > 0:
                logger.info(f"Auto-indexación en background de {resultado['registros_insertados']} registros en ChromaDB...")
                threading.Thread(target=lambda: analysis_agent.indexar_datos_reporte(codigo), daemon=True).start()
        except Exception as e:
            logger.warning(f"Error lanzando auto-indexación en background (no crítico): {e}")
        
        return jsonify({
            'success': True,
            'registros_insertados': resultado['registros_insertados'],
            'registros_error': resultado['registros_error'],
            'message': f"Se procesaron {resultado['registros_insertados']} registros",
            'auto_indexado': 'en_progreso'
        }), 200
        
    except Exception as e:
        logger.error(f"Error subiendo datos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/<codigo>/datos', methods=['GET'])
def obtener_datos(codigo):
    """Obtener datos de un reporte"""
    try:
        limite = request.args.get('limite', 100, type=int)
        datos = db_manager.consultar_datos(codigo, limite=limite)
        return jsonify(datos), 200
    except Exception as e:
        logger.error(f"Error obteniendo datos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/<codigo>/campos', methods=['GET'])
def obtener_campos(codigo):
    """Obtener nombres de campos del reporte (configurados o inferidos)."""
    try:
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado o inactivo'}), 404

        campos = reporte.get('campos') or []
        origen = 'config'
        if isinstance(campos, str):
            try:
                import json as _json
                campos = _json.loads(campos)
            except Exception:
                campos = []

        if not campos:
            muestra = db_manager.consultar_datos(codigo, limite=1)
            if muestra:
                datos_dict = muestra[0].get('datos', {})
                campos = [
                    {
                        'nombre': k,
                        'etiqueta': k,
                        'descripcion': 'Inferido desde datos',
                        'tipo_dato': 'texto'
                    } for k in datos_dict.keys()
                ]
                origen = 'inferido'

        return jsonify({
            'origen': origen,
            'total_campos': len(campos),
            'campos': campos
        }), 200
    except Exception as e:
        logger.error(f"Error obteniendo campos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/<codigo>/estadisticas', methods=['GET'])
def estadisticas_reporte(codigo):
    """Obtener estadísticas de un reporte"""
    try:
        stats = db_manager.obtener_estadisticas(codigo)
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# API - AUTENTICACIÓN Y USUARIOS
# ============================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Autenticar usuario"""
    try:
        datos = request.json
        username = datos.get('username')
        password = datos.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
        
        usuario = db_manager.autenticar_usuario(username, password)
        
        if usuario:
            return jsonify({
                'success': True,
                'usuario': usuario,
                'message': f"Bienvenido {usuario['nombre']}"
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Credenciales inválidas'
            }), 401
            
    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    """Listar todos los usuarios"""
    try:
        usuarios = db_manager.obtener_usuarios()
        return jsonify(usuarios), 200
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios', methods=['POST'])
def crear_usuario():
    """Crear nuevo usuario"""
    try:
        datos = request.json
        
        if not datos.get('username') or not datos.get('password') or not datos.get('nombre'):
            return jsonify({'error': 'Username, password y nombre son obligatorios'}), 400
        
        user_id = db_manager.crear_usuario(
            username=datos['username'],
            password=datos['password'],  # En producción, hashear con bcrypt
            nombre=datos['nombre'],
            grupo_id=datos.get('grupo_id'),
            estado=datos.get('estado', 'activo')
        )
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'message': 'Usuario creado correctamente'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creando usuario: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios/<int:user_id>', methods=['PUT'])
def actualizar_usuario(user_id):
    """Actualizar usuario"""
    try:
        datos = request.json
        success = db_manager.actualizar_usuario(user_id, datos)
        
        if success:
            return jsonify({'success': True, 'message': 'Usuario actualizado'}), 200
        else:
            return jsonify({'error': 'Usuario no encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Error actualizando usuario: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# API - GRUPOS
# ============================================

@app.route('/api/grupos', methods=['GET'])
def listar_grupos():
    """Listar todos los grupos"""
    try:
        grupos = db_manager.obtener_grupos()
        return jsonify(grupos), 200
    except Exception as e:
        logger.error(f"Error listando grupos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/grupos', methods=['POST'])
def crear_grupo():
    """Crear nuevo grupo"""
    try:
        datos = request.json
        
        if not datos.get('codigo') or not datos.get('nombre'):
            return jsonify({'error': 'Código y nombre son obligatorios'}), 400
        
        grupo_id = db_manager.crear_grupo(
            codigo=datos['codigo'],
            nombre=datos['nombre'],
            descripcion=datos.get('descripcion', ''),
            estado=datos.get('estado', 'activo')
        )
        
        return jsonify({
            'success': True,
            'grupo_id': grupo_id,
            'message': 'Grupo creado correctamente'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creando grupo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/grupos/<int:grupo_id>', methods=['PUT'])
def actualizar_grupo(grupo_id):
    """Actualizar grupo"""
    try:
        datos = request.json
        success = db_manager.actualizar_grupo(grupo_id, datos)
        
        if success:
            return jsonify({'success': True, 'message': 'Grupo actualizado'}), 200
        else:
            return jsonify({'error': 'Grupo no encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Error actualizando grupo: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# API - PERMISOS
# ============================================

@app.route('/api/permisos/grupo/<int:grupo_id>', methods=['GET'])
def obtener_permisos_grupo(grupo_id):
    """Obtener permisos de un grupo"""
    try:
        permisos = db_manager.obtener_permisos_grupo(grupo_id)
        return jsonify(permisos), 200
    except Exception as e:
        logger.error(f"Error obteniendo permisos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/permisos/grupo/<int:grupo_id>/reporte/<reporte_codigo>', methods=['POST'])
def asignar_permiso(grupo_id, reporte_codigo):
    """Asignar o actualizar permiso de grupo sobre reporte"""
    try:
        datos = request.json
        
        permiso_id = db_manager.asignar_permiso_grupo(
            grupo_id=grupo_id,
            reporte_codigo=reporte_codigo,
            puede_ver=datos.get('puede_ver', True),
            puede_crear=datos.get('puede_crear', False),
            puede_editar=datos.get('puede_editar', False),
            puede_eliminar=datos.get('puede_eliminar', False)
        )
        
        return jsonify({
            'success': True,
            'permiso_id': permiso_id,
            'message': 'Permiso asignado correctamente'
        }), 200
        
    except Exception as e:
        logger.error(f"Error asignando permiso: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/permisos/grupo/<int:grupo_id>/reporte/<reporte_codigo>', methods=['DELETE'])
def eliminar_permiso(grupo_id, reporte_codigo):
    """Eliminar permiso de grupo sobre reporte"""
    try:
        success = db_manager.eliminar_permiso_grupo(grupo_id, reporte_codigo)
        
        if success:
            return jsonify({'success': True, 'message': 'Permiso eliminado'}), 200
        else:
            return jsonify({'error': 'Permiso no encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Error eliminando permiso: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/permisos/usuario/<int:user_id>/reportes', methods=['GET'])
def obtener_reportes_usuario(user_id):
    """Obtener reportes permitidos para un usuario"""
    try:
        reportes_codigos = db_manager.obtener_reportes_permitidos_usuario(user_id)
        
        # Obtener detalles de los reportes
        reportes = []
        for codigo in reportes_codigos:
            reporte = db_manager.obtener_reporte(codigo)
            if reporte:
                reportes.append(reporte)
        
        return jsonify(reportes), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo reportes del usuario: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# API - CONSULTA DE DATOS DINÁMICOS
# ============================================

@app.route('/api/query/<codigo>', methods=['GET'])
def consultar_datos_reporte(codigo):
    """
    Endpoint dinámico para consultar datos de un reporte
    Parámetros de query:
    - fecha_inicio: Fecha de inicio (formato YYYY-MM-DD)
    - fecha_fin: Fecha de fin (formato YYYY-MM-DD)
    - limite: Número máximo de registros (default: 100)
    - campo_*: Filtros personalizados por campo
    """
    try:
        # Obtener configuración del reporte
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        # Obtener parámetros de consulta
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        limite = request.args.get('limite', 100, type=int)
        
        # Usar consulta básica por ahora
        datos = db_manager.consultar_datos(codigo, limite=limite)
        
        # Aplicar filtros manualmente si se proporcionan
        if fecha_inicio or fecha_fin:
            datos_filtrados = []
            for dato in datos:
                datos_dict = dato.get('datos', {})
                # Intentar filtrar por fecha si existe un campo de fecha
                fecha_campo = None
                for campo_key in datos_dict.keys():
                    if 'fecha' in campo_key.lower():
                        fecha_campo = datos_dict.get(campo_key)
                        break
                
                if fecha_campo:
                    incluir = True
                    if fecha_inicio and str(fecha_campo) < fecha_inicio:
                        incluir = False
                    if fecha_fin and str(fecha_campo) > fecha_fin:
                        incluir = False
                    if incluir:
                        datos_filtrados.append(dato)
                else:
                    datos_filtrados.append(dato)
            
            datos = datos_filtrados
        
        return jsonify({
            'success': True,
            'reporte': reporte['nombre'],
            'total': len(datos),
            'datos': datos
        }), 200
        
    except Exception as e:
        logger.error(f"Error consultando datos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/query/<codigo>/export', methods=['GET'])
def exportar_datos_reporte(codigo):
    """Exportar datos de un reporte a Excel"""
    try:
        # Obtener los mismos parámetros que la consulta normal
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        limite = request.args.get('limite', 1000, type=int)
        
        filtros_custom = {}
        for key, value in request.args.items():
            if key.startswith('campo_'):
                campo_nombre = key.replace('campo_', '')
                filtros_custom[campo_nombre] = value
        
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        datos = db_manager.consultar_datos_filtrado(
            codigo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limite=limite,
            filtros=filtros_custom
        )
        
        if not datos:
            return jsonify({'error': 'No hay datos para exportar'}), 404
        
        # Convertir a DataFrame
        registros = [d['datos'] for d in datos]
        df = pd.DataFrame(registros)
        
        # Crear Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=reporte['nombre'][:30])
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{codigo}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        
    except Exception as e:
        logger.error(f"Error exportando datos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats/<codigo>', methods=['GET'])
def obtener_estadisticas(codigo):
    """Obtener estadísticas de un reporte"""
    try:
        # Verificar que el reporte existe
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        # Consultar total de registros
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as total,
                   MAX(created_at) as ultimo_registro
            FROM datos_reportes
            WHERE reporte_codigo = %s
        """, (codigo,))
        
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            'total': resultado[0] if resultado else 0,
            'ultimo_registro': resultado[1].isoformat() if resultado and resultado[1] else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/upload/<codigo>', methods=['POST'])
def webhook_upload(codigo):
    """Webhook para recibir datos desde n8n u otras integraciones"""
    try:
        # Verificar que el reporte existe
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        # Obtener datos del body
        if not request.is_json:
            return jsonify({'error': 'El contenido debe ser JSON'}), 400
        
        payload = request.get_json()
        
        # Esperar formato: { "datos": [...] } o directamente [...]
        if isinstance(payload, dict) and 'datos' in payload:
            datos_lista = payload['datos']
        elif isinstance(payload, list):
            datos_lista = payload
        else:
            return jsonify({'error': 'Formato inválido. Envíe { "datos": [...] } o [...]'}), 400
        
        if not isinstance(datos_lista, list):
            return jsonify({'error': 'Los datos deben ser una lista'}), 400
        
        # Insertar en BD
        resultado = db_manager.insertar_datos(codigo, datos_lista, usuario='webhook')
        
        # Auto-indexar en ChromaDB en background
        try:
            if resultado['registros_insertados'] > 0:
                logger.info(f"Auto-indexación en background de {resultado['registros_insertados']} registros desde webhook...")
                threading.Thread(target=lambda: analysis_agent.indexar_datos_reporte(codigo), daemon=True).start()
        except Exception as e:
            logger.warning(f"Error lanzando auto-indexación en background: {e}")
        
        return jsonify({
            'success': True,
            'reporte': reporte['nombre'],
            'registros_insertados': resultado['registros_insertados'],
            'registros_error': resultado['registros_error'],
            'mensaje': f"Se procesaron {resultado['registros_insertados']} registros correctamente",
            'auto_indexado': 'en_progreso'
        }), 200
        
    except Exception as e:
        logger.error(f"Error en webhook upload: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# ENDPOINTS DE ANÁLISIS E IA
# ============================================

@app.route('/api/analysis/<codigo>/indexar', methods=['POST'])
def indexar_datos_reporte(codigo):
    """Indexar datos de un reporte para búsqueda semántica"""
    try:
        resultado = analysis_agent.indexar_datos_reporte(codigo)
        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"Error indexando datos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<codigo>/pregunta', methods=['POST'])
def hacer_pregunta(codigo):
    """Hacer una pregunta sobre los datos del reporte con memoria conversacional"""
    try:
        data = request.get_json()
        pregunta = data.get('pregunta')
        session_id = data.get('session_id', 'default')  # 🆕 Soporte para sesiones
        ultimo_grafico = data.get('ultimoGrafico')  # Recibir último gráfico del frontend
        
        if not pregunta:
            return jsonify({'error': 'Se requiere una pregunta'}), 400
        
        pregunta_lower = pregunta.lower()
        
        # Detectar si se pide DESCARGAR EL GRÁFICO como imagen/PDF
        palabras_descarga_grafico = ['descarga el gráfico', 'descarga gráfico', 'descarga el grafico', 'descarga grafico',
                                       'descargar gráfico', 'descargar grafico', 'exporta el gráfico', 'exporta el grafico']
        
        solicita_imagen_grafico = any(frase in pregunta_lower for frase in palabras_descarga_grafico)
        
        if solicita_imagen_grafico and ultimo_grafico:
            # Generar imagen PNG del gráfico
            logger.info(f"Generando imagen del gráfico: {ultimo_grafico.get('grafico', {}).get('titulo')}")
            try:
                img_buffer = _generar_imagen_grafico(ultimo_grafico['grafico'])
                img_buffer.seek(0)
                
                return send_file(
                    img_buffer,
                    mimetype='image/png',
                    as_attachment=True,
                    download_name=f'Grafico_{codigo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
                )
            except Exception as e:
                logger.error(f"Error generando imagen: {e}")
                return jsonify({
                    'pregunta': pregunta,
                    'respuesta': f"⚠️ No pude generar la imagen del gráfico. {str(e)}"
                }), 200
        
        # Detectar si se solicita EXPORTAR/DESCARGAR Excel
        palabras_clave_excel = ['excel', 'exporta', 'exportar']
        
        frases_clave = [
            'exporta a excel',
            'exportar a excel',
            'descarga el excel',
            'en excel',
            'como archivo',
            'en archivo excel'
        ]
        
        solicita_excel = (
            any(palabra in pregunta_lower for palabra in palabras_clave_excel) or
            any(frase in pregunta_lower for frase in frases_clave)
        )
        
        if solicita_excel:
            logger.info(f"Generando Excel para: {pregunta}")
            
            try:
                # Si hay un último gráfico, usar esos datos filtrados
                if ultimo_grafico and ultimo_grafico.get('grafico'):
                    logger.info("Usando datos del último gráfico generado")
                    excel_buffer = _generar_excel_desde_grafico(ultimo_grafico, codigo)
                else:
                    # Si no, generar informe completo
                    logger.info("Generando informe completo")
                    informe = analysis_agent.generar_informe_personalizado(codigo, pregunta)
                    excel_buffer = _generar_excel_con_graficos_incrustados(informe)
                
                excel_buffer.seek(0)
                
                return send_file(
                    excel_buffer,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=f'Informe_{codigo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                )
            except ValueError as ve:
                logger.warning(f"No se pudo generar Excel: {ve}")
                return jsonify({
                    'pregunta': pregunta,
                    'respuesta': f"⚠️ {str(ve)}. No se puede generar el archivo Excel sin datos."
                }), 200
            except Exception as e:
                logger.error(f"Error generando Excel: {e}")
                # 🆕 Usar session_id en la respuesta
                resultado = analysis_agent.responder_pregunta(codigo, pregunta, session_id)
                return jsonify(resultado), 200
        else:
            # 🆕 Respuesta con memoria conversacional y function calling
            resultado = analysis_agent.responder_pregunta(codigo, pregunta, session_id)
            return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error respondiendo pregunta: {e}")
        return jsonify({'error': str(e)}), 500

# 🆕 NUEVOS ENDPOINTS DE GESTIÓN DE SESIONES
@app.route('/api/analysis/<codigo>/session/<session_id>/historial', methods=['GET'])
def obtener_historial_sesion(codigo, session_id):
    """Obtener historial de conversación de una sesión"""
    try:
        historial = analysis_agent.obtener_historial(session_id)
        return jsonify({
            'session_id': session_id,
            'mensajes': len(historial),
            'historial': historial
        }), 200
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<codigo>/session/<session_id>/limpiar', methods=['POST'])
def limpiar_sesion(codigo, session_id):
    """Limpiar historial de conversación de una sesión"""
    try:
        analysis_agent.limpiar_sesion(session_id)
        return jsonify({
            'success': True,
            'message': f'Sesión {session_id} limpiada',
            'session_id': session_id
        }), 200
    except Exception as e:
        logger.error(f"Error limpiando sesión: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<codigo>/analisis', methods=['GET'])
def generar_analisis(codigo):
    """Generar análisis IA de los datos"""
    try:
        tipo = request.args.get('tipo', 'general')
        resultado = analysis_agent.generar_analisis_ia(codigo, tipo)
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error generando análisis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<codigo>/informe', methods=['GET'])
def generar_informe_completo(codigo):
    """Generar informe completo con múltiples análisis"""
    try:
        resultado = analysis_agent.generar_informe_completo(codigo)
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error generando informe: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<codigo>/buscar', methods=['POST'])
def buscar_con_lenguaje_natural(codigo):
    """Buscar datos usando lenguaje natural"""
    try:
        data = request.get_json()
        consulta = data.get('consulta')
        limite = data.get('limite', 5)
        
        if not consulta:
            return jsonify({'error': 'Se requiere una consulta'}), 400
        
        resultado = analysis_agent.consultar_con_lenguaje_natural(codigo, consulta, limite)
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<codigo>/exportar', methods=['GET'])
def exportar_analisis_excel(codigo):
    """Exportar análisis a Excel"""
    try:
        tipo = request.args.get('tipo', 'general')
        
        # Generar análisis
        analisis = analysis_agent.generar_analisis_ia(codigo, tipo)
        
        # Obtener datos del reporte
        datos = db_manager.consultar_datos(codigo, limite=1000)
        df_datos = pd.DataFrame([d['datos'] for d in datos])
        
        # Crear archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Formato para títulos
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'bg_color': '#4285F4',
                'font_color': 'white',
                'align': 'center'
            })
            
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#E8F0FE',
                'border': 1
            })
            
            # Hoja 1: Análisis
            worksheet1 = workbook.add_worksheet('Análisis IA')
            worksheet1.write('A1', f'Análisis {tipo.title()}', title_format)
            worksheet1.write('A3', 'Reporte:')
            worksheet1.write('B3', analisis['reporte'])
            worksheet1.write('A4', 'Fecha:')
            worksheet1.write('B4', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            worksheet1.write('A5', 'Total Registros:')
            worksheet1.write('B5', analisis['total_registros'])
            
            # Análisis de texto
            worksheet1.write('A7', 'Análisis:', header_format)
            worksheet1.merge_range('A8:F30', analisis['analisis'], workbook.add_format({'text_wrap': True, 'valign': 'top'}))
            
            # Hoja 2: Datos de gráficos
            if analisis.get('graficos'):
                worksheet2 = workbook.add_worksheet('Datos Gráficos')
                row = 0
                
                for grafico in analisis['graficos']:
                    worksheet2.write(row, 0, grafico['titulo'], title_format)
                    row += 2
                    
                    # Headers
                    worksheet2.write(row, 0, 'Categoría', header_format)
                    worksheet2.write(row, 1, 'Valor', header_format)
                    row += 1
                    
                    # Datos
                    for i, (label, valor) in enumerate(zip(grafico['labels'], grafico['datos'])):
                        worksheet2.write(row + i, 0, label)
                        worksheet2.write(row + i, 1, valor)
                    
                    row += len(grafico['labels']) + 2
                
                worksheet2.set_column('A:A', 40)
                worksheet2.set_column('B:B', 15)
            
            # Hoja 3: Datos completos (muestra)
            df_muestra = df_datos.head(100)
            df_muestra.to_excel(writer, sheet_name='Datos (Muestra)', index=False)
            
            worksheet3 = writer.sheets['Datos (Muestra)']
            for col_num, value in enumerate(df_muestra.columns.values):
                worksheet3.write(0, col_num, value, header_format)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'analisis_{codigo}_{tipo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f"Error exportando a Excel: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<codigo>/enviar-correo', methods=['POST'])
def enviar_analisis_correo(codigo):
    """Enviar análisis por correo con gráficas y Excel adjunto"""
    try:
        data = request.get_json()
        destinatarios = data.get('destinatarios', [])
        tipo = data.get('tipo', 'general')
        incluir_excel = data.get('incluir_excel', True)
        incluir_graficas = data.get('incluir_graficas', True)
        
        if not destinatarios:
            return jsonify({'error': 'Se requiere al menos un destinatario'}), 400
        
        # Validar configuración de correo
        if not app.config['MAIL_USERNAME']:
            return jsonify({'error': 'Configuración de correo no disponible. Configure MAIL_USERNAME y MAIL_PASSWORD en el archivo .env'}), 400
        
        # Generar análisis
        analisis = analysis_agent.generar_analisis_ia(codigo, tipo)
        
        # Generar gráficas como imágenes
        graficas_html = ""
        graficas_adjuntas = []
        
        if incluir_graficas and analisis.get('graficos'):
            # Generar imágenes de las gráficas
            imagenes_graficas = analysis_agent.generar_graficas_imagen(
                analisis['graficos'], 
                analisis['reporte']
            )
            
            # Construir HTML de gráficas incrustadas
            for idx, img_data in enumerate(imagenes_graficas):
                # Convertir a base64 para incrustar en HTML
                img_base64 = base64.b64encode(img_data['buffer'].read()).decode('utf-8')
                img_data['buffer'].seek(0)  # Reset para adjuntar después
                
                graficas_html += f"""
                <div style="margin: 20px 0; text-align: center;">
                    <h3 style="color: #4285F4;">{img_data['titulo']}</h3>
                    <img src="data:image/png;base64,{img_base64}" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px;" />
                </div>
                """
                
                graficas_adjuntas.append(img_data)
        
        # Crear mensaje
        msg = Message(
            subject=f'📊 Análisis {tipo.title()} - {analisis["reporte"]}',
            recipients=destinatarios
        )
        
        # Cuerpo del mensaje con gráficas incrustadas
        msg.html = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    line-height: 1.6; 
                    color: #333; 
                    margin: 0;
                    padding: 0;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #4285F4 0%, #34A853 100%); 
                    color: white; 
                    padding: 30px 20px; 
                    text-align: center; 
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{ 
                    padding: 30px 20px; 
                    background: #f5f5f5; 
                }}
                .info {{ 
                    background: white; 
                    padding: 20px; 
                    margin: 15px 0; 
                    border-left: 5px solid #4285F4; 
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .info p {{
                    margin: 8px 0;
                }}
                .analysis {{ 
                    background: white; 
                    padding: 25px; 
                    margin: 20px 0; 
                    white-space: pre-wrap; 
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .analysis h2 {{
                    color: #4285F4;
                    margin-top: 0;
                }}
                .graficas {{
                    background: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .footer {{ 
                    text-align: center; 
                    padding: 20px; 
                    color: #666; 
                    font-size: 12px; 
                    background: #e8e8e8;
                }}
                .badge {{
                    display: inline-block;
                    background: #34A853;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-left: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Análisis de Datos - {tipo.title()}</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px;">Sistema de Análisis Inteligente</p>
            </div>
            <div class="content">
                <div class="info">
                    <p><strong>📋 Reporte:</strong> {analisis['reporte']}</p>
                    <p><strong>📅 Fecha de Análisis:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    <p><strong>📊 Total de Registros Analizados:</strong> {analisis['total_registros']:,}</p>
                    <p><strong>🤖 Tipo de Análisis:</strong> <span class="badge">{tipo.upper()}</span></p>
                </div>
                
                <div class="analysis">
                    <h2>🔍 Resultado del Análisis:</h2>
                    <p>{analisis['analisis'].replace(chr(10), '<br>')}</p>
                </div>
                
                {f'<div class="graficas"><h2>📈 Visualizaciones:</h2>{graficas_html}</div>' if graficas_html else ''}
                
                <div class="info" style="border-left-color: #34A853;">
                    <p><strong>📎 Archivos Adjuntos:</strong></p>
                    <ul style="margin: 10px 0;">
                        {f'<li>📊 Archivo Excel con datos y análisis detallado</li>' if incluir_excel else ''}
                        {f'<li>📈 {len(graficas_adjuntas)} gráfica(s) en formato PNG</li>' if graficas_adjuntas else ''}
                    </ul>
                </div>
            </div>
            <div class="footer">
                <p><strong>Sistema de Análisis de Datos con IA</strong></p>
                <p>Este es un correo automático generado por el sistema</p>
                <p>⚠️ No responder a este mensaje</p>
            </div>
        </body>
        </html>
        """
        
        # Adjuntar Excel si se solicita
        if incluir_excel:
            # Generar Excel mejorado
            datos = db_manager.consultar_datos(codigo, limite=1000)
            df_datos = pd.DataFrame([d['datos'] for d in datos])
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                # Formatos
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 14,
                    'bg_color': '#4285F4',
                    'font_color': 'white',
                    'align': 'center',
                    'valign': 'vcenter'
                })
                
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#E8F0FE',
                    'border': 1,
                    'align': 'center'
                })
                
                # Hoja 1: Información del análisis
                worksheet_info = workbook.add_worksheet('📊 Análisis')
                worksheet_info.set_column('A:A', 25)
                worksheet_info.set_column('B:B', 50)
                
                worksheet_info.write('A1', f'Análisis {tipo.title()}', title_format)
                worksheet_info.write('A3', 'Reporte:', header_format)
                worksheet_info.write('B3', analisis['reporte'])
                worksheet_info.write('A4', 'Fecha:', header_format)
                worksheet_info.write('B4', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                worksheet_info.write('A5', 'Total Registros:', header_format)
                worksheet_info.write('B5', analisis['total_registros'])
                
                # Análisis de texto
                worksheet_info.write('A7', 'Resultado del Análisis:', title_format)
                worksheet_info.merge_range('A8:B40', analisis['analisis'], 
                    workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1}))
                
                # Hoja 2: Datos completos
                df_datos.to_excel(writer, sheet_name='📋 Datos', index=False)
                worksheet_datos = writer.sheets['📋 Datos']
                for col_num, value in enumerate(df_datos.columns.values):
                    worksheet_datos.write(0, col_num, value, header_format)
                    worksheet_datos.set_column(col_num, col_num, 15)
            
            output.seek(0)
            msg.attach(
                f'analisis_{codigo}_{tipo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                output.read()
            )
        
        # Adjuntar gráficas como archivos PNG
        if graficas_adjuntas:
            for idx, img_data in enumerate(graficas_adjuntas):
                img_data['buffer'].seek(0)
                nombre_archivo = f"grafica_{idx+1}_{img_data['titulo'][:30].replace(' ', '_')}.png"
                msg.attach(
                    nombre_archivo,
                    'image/png',
                    img_data['buffer'].read()
                )
        
        # Enviar correo
        mail.send(msg)
        
        return jsonify({
            'success': True,
            'mensaje': f'Análisis enviado exitosamente a {len(destinatarios)} destinatario(s)',
            'destinatarios': destinatarios,
            'adjuntos': {
                'excel': incluir_excel,
                'graficas': len(graficas_adjuntas) if graficas_adjuntas else 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error enviando correo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<codigo>/informe-personalizado', methods=['POST'])
def generar_informe_personalizado(codigo):
    """
    Generar informe personalizado basado en solicitud en lenguaje natural
    
    Body:
    {
        "solicitud": "facturación semanal agrupada por tercero",
        "exportar_excel": true,
        "enviar_correo": false,
        "destinatarios": ["email@ejemplo.com"]
    }
    """
    try:
        data = request.get_json()
        solicitud = data.get('solicitud', '')
        exportar_excel = data.get('exportar_excel', False)
        enviar_correo = data.get('enviar_correo', False)
        destinatarios = data.get('destinatarios', [])
        
        if not solicitud:
            return jsonify({'error': 'Se requiere una solicitud'}), 400
        
        # Generar informe personalizado
        logger.info(f"Generando informe personalizado: {solicitud}")
        informe = analysis_agent.generar_informe_personalizado(codigo, solicitud)
        
        resultado = {
            'success': True,
            'informe': informe,
            'mensaje': 'Informe generado exitosamente'
        }
        
        # Si se solicita exportar a Excel
        if exportar_excel:
            try:
                excel_buffer = _generar_excel_con_graficos_incrustados(informe)
                
                if enviar_correo and destinatarios:
                    # Enviar por correo con Excel adjunto
                    _enviar_informe_por_correo(informe, excel_buffer, destinatarios)
                    resultado['correo_enviado'] = True
                    resultado['destinatarios'] = destinatarios
                else:
                    # Retornar Excel para descarga
                    excel_buffer.seek(0)
                    return send_file(
                        excel_buffer,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True,
                        download_name=f'Informe_{codigo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    )
                    
            except Exception as e:
                logger.error(f"Error generando Excel: {e}")
                resultado['error_excel'] = str(e)
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error generando informe personalizado: {e}")
        return jsonify({'error': str(e)}), 500

def _generar_imagen_grafico(grafico: dict) -> BytesIO:
    """Generar imagen PNG de un gráfico usando matplotlib con alta calidad"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    
    # Configurar estilo
    plt.style.use('seaborn-v0_8-darkgrid')
    
    fig, ax = plt.subplots(figsize=(14, 7), dpi=150)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#f8f9fa')
    
    labels = grafico.get('labels', [])
    datos = grafico.get('datos', [])
    tipo = grafico.get('tipo', 'bar')
    titulo = grafico.get('titulo', 'Gráfico')
    
    # Colores mejorados (mismo esquema que Chart.js)
    colors = ['#4285F4', '#34A853', '#FBBC04', '#EA4335', '#9C27B0', '#00BCD4', '#FF9800', '#795548']
    
    if tipo == 'bar':
        bars = ax.bar(labels, datos, color=colors[:len(datos)], 
                     edgecolor='white', linewidth=1.5, alpha=0.85)
        
        # Configurar eje Y con formato de moneda
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        ax.set_ylabel('Valor Facturado', fontsize=13, fontweight='bold', color='#2c3e50')
        ax.set_xlabel('')
        
        # Rotar labels si son largos
        if any(len(str(label)) > 10 for label in labels):
            plt.xticks(rotation=45, ha='right', fontsize=11)
        else:
            plt.xticks(fontsize=11)
        
        # Agregar valores encima de las barras con mejor formato
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'${height:,.0f}',
                   ha='center', va='bottom', fontsize=10, 
                   fontweight='bold', color='#2c3e50')
        
        # Grid más sutil
        ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.7)
        ax.set_axisbelow(True)
        
    elif tipo == 'pie':
        # Calcular porcentajes
        total = sum(datos)
        porcentajes = [(d/total)*100 for d in datos]
        
        # Crear función para mostrar porcentaje y valor
        def autopct_format(pct, allvals):
            absolute = int(pct/100.*sum(allvals))
            return f'{pct:.1f}%\n${absolute:,.0f}'
        
        wedges, texts, autotexts = ax.pie(
            datos, 
            labels=labels, 
            autopct=lambda pct: autopct_format(pct, datos),
            colors=colors[:len(datos)],
            startangle=90, 
            pctdistance=0.75,
            explode=[0.03] * len(datos),
            shadow=True
        )
        
        # Mejorar estilo de textos
        for text in texts:
            text.set_fontsize(11)
            text.set_fontweight('bold')
            text.set_color('#2c3e50')
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')
        
        # Fondo blanco para pie charts
        ax.set_facecolor('white')
    
    # Título mejorado
    ax.set_title(titulo, fontsize=16, fontweight='bold', pad=25, color='#1a1a1a')
    
    # Ajustar márgenes
    plt.tight_layout(pad=2.0)
    
    # Guardar en buffer con alta calidad
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', 
                facecolor='white', edgecolor='none', pad_inches=0.3)
    plt.close(fig)
    buf.seek(0)
    
    return buf

def _generar_excel_desde_grafico(ultimo_grafico: dict, codigo: str) -> BytesIO:
    """Generar Excel con los datos específicos del gráfico mostrado"""
    import xlsxwriter
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    grafico = ultimo_grafico['grafico']
    labels = grafico.get('labels', [])
    datos = grafico.get('datos', [])
    titulo = grafico.get('titulo', 'Análisis')
    columna = grafico.get('columna', 'Categoría')
    
    # Hoja 1: Datos
    worksheet_datos = workbook.add_worksheet('Datos')
    
    # Formatos
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4285F4',
        'font_color': 'white',
        'border': 1
    })
    
    number_format = workbook.add_format({
        'num_format': '$#,##0'
    })
    
    # Escribir encabezados
    worksheet_datos.write(0, 0, columna, header_format)
    worksheet_datos.write(0, 1, 'Valor', header_format)
    
    # Escribir datos
    for i, (label, valor) in enumerate(zip(labels, datos), start=1):
        worksheet_datos.write(i, 0, str(label))
        worksheet_datos.write(i, 1, valor, number_format)
    
    worksheet_datos.set_column(0, 0, 30)
    worksheet_datos.set_column(1, 1, 20)
    
    # Hoja 2: Gráfico
    worksheet_grafico = workbook.add_worksheet('Gráfico')
    
    chart = workbook.add_chart({'type': 'column'})
    
    chart.add_series({
        'name': titulo,
        'categories': ['Datos', 1, 0, len(labels), 0],
        'values': ['Datos', 1, 1, len(labels), 1],
        'fill': {'color': '#4285F4'},
        'data_labels': {'value': True, 'num_format': '$#,##0'}
    })
    
    chart.set_title({'name': titulo})
    chart.set_x_axis({'name': columna})
    chart.set_y_axis({'name': 'Valor', 'num_format': '$#,##0'})
    chart.set_legend({'position': 'none'})
    chart.set_size({'width': 720, 'height': 400})
    
    worksheet_grafico.insert_chart('B2', chart)
    
    # Hoja 3: Resumen
    worksheet_resumen = workbook.add_worksheet('Resumen')
    
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'font_color': '#4285F4'
    })
    
    worksheet_resumen.write(0, 0, titulo, title_format)
    worksheet_resumen.write(2, 0, 'Total de elementos:', header_format)
    worksheet_resumen.write(2, 1, len(labels))
    worksheet_resumen.write(3, 0, 'Valor total:', header_format)
    worksheet_resumen.write(3, 1, sum(datos), number_format)
    worksheet_resumen.write(4, 0, 'Valor promedio:', header_format)
    worksheet_resumen.write(4, 1, sum(datos) / len(datos) if len(datos) > 0 else 0, number_format)
    worksheet_resumen.write(5, 0, 'Valor máximo:', header_format)
    worksheet_resumen.write(5, 1, max(datos) if datos else 0, number_format)
    worksheet_resumen.write(5, 2, labels[datos.index(max(datos))] if datos else '')
    
    worksheet_resumen.set_column(0, 0, 20)
    worksheet_resumen.set_column(1, 2, 18)
    
    workbook.close()
    output.seek(0)
    
    return output

def _generar_excel_con_graficos_incrustados(informe: dict) -> BytesIO:
    """Generar Excel con gráficos incrustados de Excel (nativos)"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formatos
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#4285F4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter'
        })
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8F0FE',
            'border': 1
        })
        data_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        
        # Hoja 1: Resumen Ejecutivo
        worksheet_resumen = workbook.add_worksheet('📊 Resumen Ejecutivo')
        worksheet_resumen.set_column('A:A', 20)
        worksheet_resumen.set_column('B:B', 80)
        
        row = 0
        worksheet_resumen.write(row, 0, 'Reporte:', header_format)
        worksheet_resumen.write(row, 1, informe['reporte'], data_format)
        row += 1
        
        worksheet_resumen.write(row, 0, 'Solicitud:', header_format)
        worksheet_resumen.write(row, 1, informe['solicitud'], data_format)
        row += 1
        
        worksheet_resumen.write(row, 0, 'Fecha:', header_format)
        worksheet_resumen.write(row, 1, informe['fecha_generacion'], data_format)
        row += 2
        
        worksheet_resumen.write(row, 0, 'Registros Totales:', header_format)
        worksheet_resumen.write(row, 1, informe['total_registros'], data_format)
        row += 1
        
        worksheet_resumen.write(row, 0, 'Registros Procesados:', header_format)
        worksheet_resumen.write(row, 1, informe['registros_procesados'], data_format)
        row += 3
        
        # Resumen ejecutivo
        if informe.get('resumen_ejecutivo'):
            worksheet_resumen.write(row, 0, 'RESUMEN EJECUTIVO', title_format)
            row += 1
            worksheet_resumen.merge_range(row, 0, row + 15, 1, 
                informe['resumen_ejecutivo'],
                workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
            )
        
        # Hoja 2: Datos Procesados
        if informe.get('datos_procesados'):
            df_procesado = pd.DataFrame(informe['datos_procesados'])
            df_procesado.to_excel(writer, sheet_name='📋 Datos Agrupados', index=False)
            
            worksheet_datos = writer.sheets['📋 Datos Agrupados']
            for col_num, value in enumerate(df_procesado.columns.values):
                worksheet_datos.write(0, col_num, value, header_format)
                # Ajustar ancho de columna
                max_len = max(
                    df_procesado[value].astype(str).apply(len).max(),
                    len(str(value))
                )
                worksheet_datos.set_column(col_num, col_num, min(max_len + 2, 50))
        
        # Hoja 3: Gráficos (con gráficos nativos de Excel)
        if informe.get('graficos'):
            worksheet_graficos = workbook.add_worksheet('📈 Gráficos')
            worksheet_graficos.write(0, 0, 'VISUALIZACIONES', title_format)
            
            row_grafico = 2
            
            for idx, grafico_data in enumerate(informe['graficos']):
                tipo = grafico_data.get('tipo', 'bar')
                titulo = grafico_data.get('titulo', f'Gráfico {idx+1}')
                labels = grafico_data.get('labels', [])
                datos = grafico_data.get('datos', [])
                
                if not labels or not datos:
                    continue
                
                # Escribir datos del gráfico en columnas
                col_inicio = 0
                worksheet_graficos.write(row_grafico, col_inicio, 'Categoría', header_format)
                worksheet_graficos.write(row_grafico, col_inicio + 1, 'Valor', header_format)
                
                for i, (label, valor) in enumerate(zip(labels, datos)):
                    worksheet_graficos.write(row_grafico + 1 + i, col_inicio, str(label))
                    worksheet_graficos.write(row_grafico + 1 + i, col_inicio + 1, valor, number_format)
                
                # Crear gráfico nativo de Excel
                if tipo == 'bar':
                    chart = workbook.add_chart({'type': 'column'})
                elif tipo == 'pie':
                    chart = workbook.add_chart({'type': 'pie'})
                elif tipo == 'line':
                    chart = workbook.add_chart({'type': 'line'})
                else:
                    chart = workbook.add_chart({'type': 'column'})
                
                # Configurar serie de datos
                chart.add_series({
                    'name': titulo,
                    'categories': ['📈 Gráficos', row_grafico + 1, col_inicio, 
                                  row_grafico + len(labels), col_inicio],
                    'values': ['📈 Gráficos', row_grafico + 1, col_inicio + 1,
                              row_grafico + len(labels), col_inicio + 1],
                    'data_labels': {'value': True, 'num_format': '#,##0'},
                })
                
                # Configurar título y estilo
                chart.set_title({'name': titulo})
                chart.set_legend({'position': 'bottom'})
                chart.set_size({'width': 600, 'height': 400})
                chart.set_style(11)
                
                # Insertar gráfico
                worksheet_graficos.insert_chart(row_grafico, col_inicio + 3, chart)
                
                # Mover a siguiente posición
                row_grafico += len(labels) + 25
        
        # Hoja 4: Estadísticas
        if informe.get('estadisticas'):
            worksheet_stats = workbook.add_worksheet('📈 Estadísticas')
            worksheet_stats.write(0, 0, 'ESTADÍSTICAS GENERALES', title_format)
            
            row = 2
            for stat_type, valores in informe['estadisticas'].items():
                if valores:
                    worksheet_stats.write(row, 0, stat_type.upper(), header_format)
                    row += 1
                    for campo, valor in valores.items():
                        worksheet_stats.write(row, 0, campo)
                        if isinstance(valor, (int, float)):
                            worksheet_stats.write(row, 1, valor, number_format)
                        else:
                            worksheet_stats.write(row, 1, str(valor))
                        row += 1
                    row += 1
    
    output.seek(0)
    return output

def _enviar_informe_por_correo(informe: dict, excel_buffer: BytesIO, destinatarios: list):
    """Enviar informe por correo con Excel y gráficos adjuntos"""
    try:
        # Validar configuración
        if not app.config['MAIL_USERNAME']:
            raise ValueError('Configuración de correo no disponible')
        
        # Crear mensaje
        msg = Message(
            subject=f'📊 Informe Personalizado: {informe["solicitud"]}',
            recipients=destinatarios
        )
        
        # Generar gráficos como imágenes
        graficas_imagenes = []
        if informe.get('graficos'):
            graficas_imagenes = analysis_agent.generar_graficas_imagen(
                informe['graficos'],
                informe['reporte']
            )
        
        # Construir HTML con gráficos incrustados
        graficas_html = ""
        for img_data in graficas_imagenes:
            img_base64 = base64.b64encode(img_data['buffer'].read()).decode('utf-8')
            img_data['buffer'].seek(0)
            
            graficas_html += f"""
            <div style="margin: 30px 0; text-align: center; page-break-inside: avoid;">
                <h3 style="color: #4285F4; margin-bottom: 15px;">{img_data['titulo']}</h3>
                <img src="data:image/png;base64,{img_base64}" 
                     style="max-width: 100%; height: auto; border: 2px solid #E8F0FE; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />
            </div>
            """
        
        # HTML del correo
        msg.html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #4285F4 0%, #34A853 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; background: #f5f5f5; }}
                .info-box {{ background: white; padding: 20px; margin: 15px 0; border-left: 5px solid #4285F4; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .summary {{ background: white; padding: 25px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); white-space: pre-wrap; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Informe Personalizado</h1>
                <p style="margin: 10px 0;">{informe['reporte']}</p>
            </div>
            
            <div class="content">
                <div class="info-box">
                    <h3 style="color: #4285F4; margin-top: 0;">Detalles del Informe</h3>
                    <p><strong>Solicitud:</strong> {informe['solicitud']}</p>
                    <p><strong>Fecha de Generación:</strong> {informe['fecha_generacion']}</p>
                    <p><strong>Total de Registros:</strong> {informe['total_registros']:,}</p>
                    <p><strong>Registros Procesados:</strong> {informe['registros_procesados']:,}</p>
                </div>
                
                {'<div class="summary"><h3 style="color: #4285F4; margin-top: 0;">Resumen Ejecutivo</h3>' + informe.get('resumen_ejecutivo', 'No disponible') + '</div>' if informe.get('resumen_ejecutivo') else ''}
                
                <div style="background: white; padding: 25px; margin: 20px 0; border-radius: 8px;">
                    <h2 style="color: #4285F4; margin-top: 0;">Visualizaciones</h2>
                    {graficas_html}
                </div>
            </div>
            
            <div class="footer">
                <p>Este es un mensaje automático del Sistema de Análisis con IA</p>
                <p>Los datos completos están disponibles en el archivo Excel adjunto</p>
            </div>
        </body>
        </html>
        """
        
        # Adjuntar Excel
        excel_buffer.seek(0)
        msg.attach(
            f'Informe_{informe["codigo"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            excel_buffer.read()
        )
        
        # Adjuntar gráficas PNG
        for idx, img_data in enumerate(graficas_imagenes):
            img_data['buffer'].seek(0)
            msg.attach(
                f'grafico_{idx+1}.png',
                'image/png',
                img_data['buffer'].read()
            )
        
        # Enviar
        mail.send(msg)
        logger.info(f"Informe enviado a {len(destinatarios)} destinatario(s)")
        
    except Exception as e:
        logger.error(f"Error enviando informe por correo: {e}")
        raise

# ============================================
# ENDPOINTS: CONTROL DE PERIODOS Y CARGAS
# ============================================

@app.route('/api/reportes/crear-con-validacion', methods=['POST'])
def crear_reporte_con_validacion():
    """
    Crear un nuevo reporte con validación de IA
    Puede recibir campos manuales o archivo Excel
    """
    try:
        from validador_ia import validador_ia
        
        data = request.get_json()
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        campos = data.get('campos', [])  # Lista de {nombre, tipo, descripcion}
        datos_muestra = data.get('datos_muestra', [])  # Opcional: datos de ejemplo
        
        if not nombre:
            return jsonify({"error": "Nombre del reporte requerido"}), 400
        
        if not campos or len(campos) < 1:
            return jsonify({"error": "Debe proporcionar al menos 1 campo"}), 400
        
        # Validar con IA
        validacion = validador_ia.validar_estructura_reporte(
            nombre_reporte=nombre,
            campos=campos,
            datos_muestra=datos_muestra,
            descripcion=descripcion
        )
        
        # Si no es válido, devolver para que usuario aclare
        if not validacion['valido']:
            return jsonify({
                "validacion_requerida": True,
                "validacion": validacion,
                "mensaje": "El reporte requiere aclaraciones antes de ser creado"
            }), 200
        
        # Si requiere aclaraciones de campos
        if validacion['campos_requieren_aclaracion']:
            return jsonify({
                "validacion_requerida": True,
                "validacion": validacion,
                "mensaje": f"{len(validacion['campos_requieren_aclaracion'])} campos requieren aclaración"
            }), 200
        
        # Si no tiene campo de fecha y necesitamos periodo
        requiere_periodo = data.get('requiere_periodo', True)
        if requiere_periodo and not validacion['tiene_campo_fecha']:
            return jsonify({
                "validacion_requerida": True,
                "validacion": validacion,
                "mensaje": "El reporte debe tener un campo de fecha para control de periodos"
            }), 200
        
        # Crear el reporte en la BD
        codigo = nombre.lower().replace(' ', '_')[:50]
        tipo_periodo = data.get('tipo_periodo') or validacion.get('tipo_periodo_sugerido', 'mensual')
        campo_fecha = data.get('campo_fecha') or validacion.get('campo_fecha_sugerido')
        
        resultado = db_manager.crear_reporte_config(
            nombre=nombre,
            codigo=codigo,
            descripcion=descripcion,
            campos=campos,
            categoria=data.get('categoria', 'general'),
            tipo_periodo=tipo_periodo,
            campo_fecha=campo_fecha,
            requiere_periodo=requiere_periodo,
            validacion_ia=validacion
        )
        
        return jsonify({
            "success": True,
            "reporte": resultado,
            "validacion": validacion,
            "mensaje": f"Reporte '{nombre}' creado exitosamente"
        }), 201
        
    except Exception as e:
        logger.error(f"Error creando reporte con validación: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/reportes/<codigo>/cargar-datos', methods=['POST'])
def cargar_datos_reporte(codigo):
    """
    Cargar datos a un reporte (Excel o manual)
    Crea registro en datos_temporales para aprobación
    """
    try:
        from validador_ia import validador_ia
        from datetime import datetime, date
        
        # Obtener configuración del reporte
        reporte_config = db_manager.obtener_reporte_por_codigo(codigo)
        if not reporte_config:
            return jsonify({"error": "Reporte no encontrado"}), 404
        
        # Obtener datos (JSON o archivo)
        if request.is_json:
            data = request.get_json()
            datos = data.get('datos', [])
            archivo_nombre = data.get('archivo_nombre', 'manual')
        else:
            # Subida de Excel
            if 'file' not in request.files:
                return jsonify({"error": "No se recibió archivo"}), 400
            
            file = request.files['file']
            archivo_nombre = file.filename
            
            # Procesar Excel
            import pandas as pd
            df = pd.read_excel(file)
            datos = df.to_dict('records')
        
        # Validar mínimo 2 registros
        if len(datos) < 2:
            return jsonify({"error": "Se requieren al menos 2 registros"}), 400
        
        # Obtener periodo de la carga
        tipo_periodo = reporte_config.get('tipo_periodo', 'mensual')
        campo_fecha = reporte_config.get('campo_fecha')
        
        if not campo_fecha:
            return jsonify({"error": "El reporte no tiene configurado campo de fecha"}), 400
        
        # Extraer fechas y calcular periodo
        fechas = []
        for registro in datos:
            fecha_str = registro.get(campo_fecha)
            if fecha_str:
                try:
                    if isinstance(fecha_str, str):
                        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    elif isinstance(fecha_str, date):
                        fecha = fecha_str
                    else:
                        fecha = datetime.fromisoformat(str(fecha_str)).date()
                    fechas.append(fecha)
                except:
                    pass
        
        if not fechas:
            return jsonify({"error": f"No se encontraron fechas válidas en el campo '{campo_fecha}'"}), 400
        
        # Calcular periodo
        fecha_referencia = min(fechas)
        periodo_calc = db_manager.ejecutar_query(
            "SELECT * FROM calcular_periodo(%s, %s)",
            (tipo_periodo, fecha_referencia)
        )[0]
        
        periodo_inicio = periodo_calc[0]
        periodo_fin = periodo_calc[1]
        
        # Validar que no se solape con cargas existentes
        validacion_periodo = db_manager.ejecutar_query(
            "SELECT * FROM validar_periodo(%s, %s, %s)",
            (codigo, periodo_inicio, periodo_fin)
        )[0]
        
        if not validacion_periodo[0]:  # No es válido
            return jsonify({
                "error": "Periodo solapado",
                "mensaje": validacion_periodo[1],
                "cargas_conflicto": validacion_periodo[2]
            }), 409
        
        # Validar estructura con IA
        validacion_datos = validador_ia.validar_datos_carga(
            reporte_codigo=codigo,
            reporte_nombre=reporte_config['nombre'],
            campos_esperados=reporte_config.get('campos', []),
            datos=datos,
            periodo_esperado={
                'tipo': tipo_periodo,
                'campo_fecha': campo_fecha,
                'inicio': periodo_inicio,
                'fin': periodo_fin
            }
        )
        
        if not validacion_datos['valido']:
            return jsonify({
                "validacion_requerida": True,
                "validacion": validacion_datos,
                "mensaje": "Los datos tienen errores de validación"
            }), 400
        
        # Crear registro de carga
        usuario = request.headers.get('X-User', 'admin')  # Obtener de sesión
        
        carga_id = db_manager.ejecutar_query(
            """
            INSERT INTO cargas_datos 
            (reporte_codigo, periodo_inicio, periodo_fin, periodo_tipo, cantidad_registros, 
             archivo_original, usuario_carga, estado, validacion_previa)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (codigo, periodo_inicio, periodo_fin, tipo_periodo, len(datos),
             archivo_nombre, usuario, 'pendiente', json.dumps(validacion_datos)),
            commit=True
        )[0][0]
        
        # Insertar datos en tabla temporal
        for idx, registro in enumerate(datos, start=1):
            db_manager.ejecutar_query(
                """
                INSERT INTO datos_temporales 
                (carga_id, reporte_codigo, datos, fila_numero)
                VALUES (%s, %s, %s, %s)
                """,
                (carga_id, codigo, json.dumps(registro), idx),
                commit=False
            )
        
        db_manager.commit()
        
        return jsonify({
            "success": True,
            "carga_id": carga_id,
            "periodo": {
                "inicio": str(periodo_inicio),
                "fin": str(periodo_fin),
                "tipo": tipo_periodo
            },
            "cantidad_registros": len(datos),
            "validacion": validacion_datos,
            "mensaje": f"Carga creada exitosamente. Pendiente de aprobación."
        }), 201
        
    except Exception as e:
        logger.error(f"Error cargando datos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/cargas/<int:carga_id>', methods=['GET'])
def obtener_carga(carga_id):
    """Obtener detalles de una carga"""
    try:
        carga = db_manager.ejecutar_query(
            "SELECT * FROM v_resumen_cargas WHERE id = %s",
            (carga_id,)
        )
        
        if not carga:
            return jsonify({"error": "Carga no encontrada"}), 404
        
        # Convertir a dict
        carga_dict = dict(zip(
            ['id', 'reporte_codigo', 'reporte_nombre', 'periodo_tipo', 'periodo_inicio', 
             'periodo_fin', 'cantidad_registros', 'estado', 'usuario_carga', 'fecha_carga',
             'fecha_aprobacion', 'aprobado_por', 'archivo_original', 'registros_pendientes',
             'registros_aprobados'],
            carga[0]
        ))
        
        # Obtener muestra de datos temporales
        datos_temp = db_manager.ejecutar_query(
            """
            SELECT datos, fila_numero, errores 
            FROM datos_temporales 
            WHERE carga_id = %s 
            ORDER BY fila_numero 
            LIMIT 10
            """,
            (carga_id,)
        )
        
        carga_dict['datos_muestra'] = [
            {
                'fila': row[1],
                'datos': json.loads(row[0]) if isinstance(row[0], str) else row[0],
                'errores': json.loads(row[2]) if row[2] else None
            }
            for row in datos_temp
        ]
        
        return jsonify(carga_dict), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo carga: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/cargas/<int:carga_id>/aprobar', methods=['POST'])
def aprobar_carga(carga_id):
    """Aprobar carga y mover datos a tabla definitiva"""
    try:
        from datetime import datetime
        
        # Obtener información de la carga
        carga = db_manager.ejecutar_query(
            "SELECT reporte_codigo, estado, cantidad_registros FROM cargas_datos WHERE id = %s",
            (carga_id,)
        )
        
        if not carga:
            return jsonify({"error": "Carga no encontrada"}), 404
        
        reporte_codigo, estado, cantidad = carga[0]
        
        if estado == 'aprobado':
            return jsonify({"error": "La carga ya fue aprobada"}), 400
        
        # Obtener usuario que aprueba
        data = request.get_json() or {}
        usuario = data.get('usuario', request.headers.get('X-User', 'admin'))
        notas = data.get('notas', '')
        
        # Mover datos de temporal a definitivo
        db_manager.ejecutar_query(
            """
            INSERT INTO datos_reportes (reporte_codigo, datos, carga_id, fecha_periodo, periodo_inicio, periodo_fin, uploaded_by)
            SELECT 
                reporte_codigo,
                datos,
                carga_id,
                fecha_extraida,
                periodo_inicio,
                periodo_fin,
                %s
            FROM datos_temporales
            WHERE carga_id = %s
            """,
            (usuario, carga_id),
            commit=False
        )
        
        # Actualizar estado de carga
        db_manager.ejecutar_query(
            """
            UPDATE cargas_datos 
            SET estado = 'aprobado', 
                fecha_aprobacion = %s, 
                aprobado_por = %s,
                notas = %s
            WHERE id = %s
            """,
            (datetime.now(), usuario, notas, carga_id),
            commit=False
        )
        
        # Borrar datos temporales (ya están en definitiva)
        db_manager.ejecutar_query(
            "DELETE FROM datos_temporales WHERE carga_id = %s",
            (carga_id,),
            commit=True
        )
        
        # Reindexar en ChromaDB
        try:
            indexar_datos_reporte(reporte_codigo)
        except Exception as e:
            logger.warning(f"Error reindexando después de aprobar: {e}")
        
        return jsonify({
            "success": True,
            "mensaje": f"Carga aprobada. {cantidad} registros movidos a datos definitivos.",
            "reporte_codigo": reporte_codigo
        }), 200
        
    except Exception as e:
        logger.error(f"Error aprobando carga: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/cargas/<int:carga_id>/rechazar', methods=['POST'])
def rechazar_carga(carga_id):
    """Rechazar carga y eliminar datos temporales"""
    try:
        data = request.get_json() or {}
        razon = data.get('razon', 'No especificada')
        usuario = data.get('usuario', request.headers.get('X-User', 'admin'))
        
        # Actualizar estado
        db_manager.ejecutar_query(
            """
            UPDATE cargas_datos 
            SET estado = 'rechazado', 
                errores_validacion = %s,
                aprobado_por = %s
            WHERE id = %s
            """,
            (razon, usuario, carga_id),
            commit=False
        )
        
        # Eliminar datos temporales
        db_manager.ejecutar_query(
            "DELETE FROM datos_temporales WHERE carga_id = %s",
            (carga_id,),
            commit=True
        )
        
        return jsonify({
            "success": True,
            "mensaje": "Carga rechazada y datos temporales eliminados"
        }), 200
        
    except Exception as e:
        logger.error(f"Error rechazando carga: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reportes/<codigo>/cargas', methods=['GET'])
def listar_cargas_reporte(codigo):
    """Listar historial de cargas de un reporte"""
    try:
        estado_filtro = request.args.get('estado')  # pendiente, aprobado, rechazado
        
        query = "SELECT * FROM v_resumen_cargas WHERE reporte_codigo = %s"
        params = [codigo]
        
        if estado_filtro:
            query += " AND estado = %s"
            params.append(estado_filtro)
        
        query += " ORDER BY fecha_carga DESC"
        
        cargas = db_manager.ejecutar_query(query, tuple(params))
        
        resultado = []
        for carga in cargas:
            resultado.append(dict(zip(
                ['id', 'reporte_codigo', 'reporte_nombre', 'periodo_tipo', 'periodo_inicio', 
                 'periodo_fin', 'cantidad_registros', 'estado', 'usuario_carga', 'fecha_carga',
                 'fecha_aprobacion', 'aprobado_por', 'archivo_original', 'registros_pendientes',
                 'registros_aprobados'],
                carga
            )))
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error listando cargas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reportes/<codigo>/datos-por-periodo', methods=['GET'])
def consultar_datos_periodo(codigo):
    """
    Consultar datos de un reporte por fecha o rango de fechas
    Query params: fecha, fecha_inicio, fecha_fin
    """
    try:
        fecha_str = request.args.get('fecha')
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')
        
        from datetime import datetime
        
        if fecha_str:
            # Consulta por fecha específica
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            
            datos = db_manager.ejecutar_query(
                """
                SELECT datos, fecha_periodo, periodo_inicio, periodo_fin, created_at
                FROM datos_reportes
                WHERE reporte_codigo = %s 
                AND fecha_periodo = %s
                ORDER BY created_at DESC
                """,
                (codigo, fecha)
            )
        elif fecha_inicio_str and fecha_fin_str:
            # Consulta por rango
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            
            datos = db_manager.ejecutar_query(
                """
                SELECT datos, fecha_periodo, periodo_inicio, periodo_fin, created_at
                FROM datos_reportes
                WHERE reporte_codigo = %s 
                AND fecha_periodo BETWEEN %s AND %s
                ORDER BY fecha_periodo, created_at DESC
                """,
                (codigo, fecha_inicio, fecha_fin)
            )
        else:
            # Sin filtro de fecha, devolver todo (limitado)
            datos = db_manager.ejecutar_query(
                """
                SELECT datos, fecha_periodo, periodo_inicio, periodo_fin, created_at
                FROM datos_reportes
                WHERE reporte_codigo = %s
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (codigo,)
            )
        
        resultado = []
        for row in datos:
            datos_json = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            resultado.append({
                'datos': datos_json,
                'fecha_periodo': str(row[1]) if row[1] else None,
                'periodo_inicio': str(row[2]) if row[2] else None,
                'periodo_fin': str(row[3]) if row[3] else None,
                'fecha_carga': str(row[4]) if row[4] else None
            })
        
        return jsonify({
            "reporte_codigo": codigo,
            "cantidad": len(resultado),
            "datos": resultado
        }), 200
        
    except Exception as e:
        logger.error(f"Error consultando datos por periodo: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# INICIALIZACIÓN
# ============================================

if __name__ == '__main__':
    # Inicializar tablas de metadatos
    db_manager.init_metadata_tables()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
