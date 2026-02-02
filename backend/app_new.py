from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import pandas as pd
from io import BytesIO
from datetime import datetime

from db_manager import DatabaseManager
from models import ReporteConfig, CampoConfig, RelacionConfig

load_dotenv()

app = Flask(__name__)
CORS(app)

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

# ============================================
# RUTAS PÚBLICAS
# ============================================

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
# INICIALIZACIÓN
# ============================================

if __name__ == '__main__':
    # Inicializar tablas de metadatos
    db_manager.init_metadata_tables()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
