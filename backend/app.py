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
from models import ReporteConfig, CampoConfig, RelacionConfig
from analysis_agent import DataAnalysisAgent

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

@app.route('/api/admin/reportes', methods=['GET'])
def listar_reportes():
    """Listar todos los reportes"""
    try:
        reportes = db_manager.listar_reportes()
        return jsonify(reportes), 200
    except Exception as e:
        logger.error(f"Error listando reportes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reportes', methods=['POST'])
def crear_reporte():
    """Crear nuevo reporte"""
    try:
        datos = request.json
        
        # Validar campos obligatorios
        if not datos.get('nombre') or not datos.get('codigo'):
            return jsonify({'error': 'Nombre y código son obligatorios'}), 400
        
        # Crear configuración
        reporte = ReporteConfig(datos)
        
        # Guardar en BD
        reporte_id = db_manager.crear_reporte(reporte)
        
        return jsonify({
            'success': True,
            'reporte_id': reporte_id,
            'message': f"Reporte '{datos['nombre']}' creado correctamente"
        }), 201
        
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
        
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': 'Solo archivos .xlsx permitidos'}), 400
        
        # Obtener configuración del reporte
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        # Leer Excel
        df = pd.read_excel(file, sheet_name='Datos')
        
        # Validar estructura
        campos_config = reporte.get('campos', [])
        if isinstance(campos_config, str):
            campos_config = json.loads(campos_config)
        
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
        
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': 'Solo archivos .xlsx permitidos'}), 400
        
        # Obtener configuración del reporte
        reporte = db_manager.obtener_reporte(codigo)
        if not reporte:
            return jsonify({'error': 'Reporte no encontrado'}), 404
        
        # Leer Excel
        df = pd.read_excel(file, sheet_name='Datos')
        
        # Validar estructura
        campos_config = reporte.get('campos', [])
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
            'registros_insertados': resultado['registros_insertados'],
            'registros_error': resultado['registros_error'],
            'message': f"Se procesaron {resultado['registros_insertados']} registros"
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
        
        return jsonify({
            'success': True,
            'reporte': reporte['nombre'],
            'registros_insertados': resultado['registros_insertados'],
            'registros_error': resultado['registros_error'],
            'mensaje': f"Se procesaron {resultado['registros_insertados']} registros correctamente"
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
    """Hacer una pregunta sobre los datos del reporte"""
    try:
        data = request.get_json()
        pregunta = data.get('pregunta')
        
        if not pregunta:
            return jsonify({'error': 'Se requiere una pregunta'}), 400
        
        resultado = analysis_agent.responder_pregunta(codigo, pregunta)
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error respondiendo pregunta: {e}")
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
# INICIALIZACIÓN
# ============================================

if __name__ == '__main__':
    # Inicializar tablas de metadatos
    db_manager.init_metadata_tables()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
