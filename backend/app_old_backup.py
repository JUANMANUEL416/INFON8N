from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from openpyxl import load_workbook
import logging

load_dotenv()

app = Flask(__name__)
CORS(app)

# Ruta a las plantillas
PLANTILLAS_DIR = '/app/data/plantillas'

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

def get_db_connection():
    """Conectar a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Error conectando a BD: {e}")
        return None

def init_database():
    """Crear tablas iniciales"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Tabla de facturas
        cur.execute('''
            CREATE TABLE IF NOT EXISTS facturas (
                id SERIAL PRIMARY KEY,
                numero_factura VARCHAR(50) UNIQUE NOT NULL,
                fecha DATE NOT NULL,
                cliente VARCHAR(255) NOT NULL,
                monto DECIMAL(12, 2) NOT NULL,
                estado VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Tabla de cartera
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cartera (
                id SERIAL PRIMARY KEY,
                numero_factura VARCHAR(50),
                cliente VARCHAR(255) NOT NULL,
                monto_adeudado DECIMAL(12, 2) NOT NULL,
                dias_vencido INT,
                estado VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Tabla de logs de carga
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cargas_archivos (
                id SERIAL PRIMARY KEY,
                nombre_archivo VARCHAR(255) NOT NULL,
                tipo_datos VARCHAR(50),
                registros INT,
                estado VARCHAR(50),
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                detalles TEXT
            );
        ''')
        
        # Tabla de productos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                id_producto VARCHAR(50) UNIQUE NOT NULL,
                nombre VARCHAR(255) NOT NULL,
                cantidad_vendida INT,
                precio_unitario DECIMAL(12, 2),
                fecha DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Tabla de gastos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS gastos (
                id SERIAL PRIMARY KEY,
                fecha DATE NOT NULL,
                categoria VARCHAR(100),
                descripcion TEXT,
                monto DECIMAL(12, 2) NOT NULL,
                area VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Base de datos inicializada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error inicializando BD: {e}")
        return False

@app.route('/', methods=['GET'])
def index():
    """Página principal de la aplicación web"""
    return render_template('index.html')

@app.route('/download/<data_type>', methods=['GET'])
def download_template(data_type):
    """Descargar plantilla Excel"""
    template_files = {
        'facturas': 'plantilla_facturacion_diaria.xlsx',
        'cartera': 'plantilla_cartera_vencida.xlsx',
        'productos': 'plantilla_ventas_productos.xlsx',
        'gastos': 'plantilla_gastos_operativos.xlsx'
    }
    
    if data_type not in template_files:
        return jsonify({'error': 'Tipo de plantilla no válido'}), 400
    
    filename = template_files[data_type]
    filepath = os.path.join(PLANTILLAS_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Plantilla no encontrada'}), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de salud"""
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({'status': 'ok', 'message': 'Backend funcionando'}), 200
    return jsonify({'status': 'error', 'message': 'BD no disponible'}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """Cargar archivo Excel"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        data_type = request.form.get('type', 'facturas')  # tipo: facturas, cartera, etc
        
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': 'Solo archivos .xlsx permitidos'}), 400
        
        # Guardar archivo
        filepath = f"/app/data/{file.filename}"
        file.save(filepath)
        
        # Procesar
        result = process_excel(filepath, data_type)
        
        return jsonify({
            'success': True,
            'message': 'Archivo procesado correctamente',
            'records': result['records_inserted'],
            'file': file.filename
        }), 200
        
    except Exception as e:
        logger.error(f"Error en upload: {e}")
        return jsonify({'error': str(e)}), 500

# Definición de modelos/plantillas
DATA_MODELS = {
    'facturas': {
        'required_columns': ['numero_factura', 'fecha', 'cliente', 'monto'],
        'optional_columns': ['estado'],
        'table': 'facturas'
    },
    'cartera': {
        'required_columns': ['cliente', 'monto_adeudado'],
        'optional_columns': ['numero_factura', 'dias_vencido', 'estado'],
        'table': 'cartera'
    },
    'productos': {
        'required_columns': ['id_producto', 'nombre', 'cantidad_vendida', 'precio_unitario', 'fecha'],
        'optional_columns': [],
        'table': 'productos'
    },
    'gastos': {
        'required_columns': ['fecha', 'categoria', 'descripcion', 'monto', 'area'],
        'optional_columns': [],
        'table': 'gastos'
    }
}

def validate_excel_structure(df, data_type):
    """Validar que el Excel tenga la estructura correcta"""
    if data_type not in DATA_MODELS:
        return {'valid': False, 'error': f'Tipo de datos no soportado: {data_type}'}
    
    model = DATA_MODELS[data_type]
    required_cols = model['required_columns']
    df_columns = df.columns.tolist()
    
    # Verificar columnas requeridas
    missing_cols = [col for col in required_cols if col not in df_columns]
    if missing_cols:
        return {
            'valid': False,
            'error': f'Faltan columnas obligatorias: {", ".join(missing_cols)}',
            'expected': required_cols
        }
    
    # Verificar que no esté vacío
    if len(df) == 0:
        return {'valid': False, 'error': 'El archivo está vacío'}
    
    return {'valid': True}

def process_excel(filepath, data_type):
    """Procesar archivo Excel e insertar en BD"""
    df = pd.read_excel(filepath)
    
    # Validar estructura
    validation = validate_excel_structure(df, data_type)
    if not validation['valid']:
        raise ValueError(validation['error'])
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        records_inserted = 0
        
        if data_type == 'facturas':
            for index, row in df.iterrows():
                cur.execute('''
                    INSERT INTO facturas (numero_factura, fecha, cliente, monto, estado)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (numero_factura) DO NOTHING
                ''', (row['numero_factura'], row['fecha'], row['cliente'], row['monto'], row.get('estado', 'pendiente')))
                records_inserted += 1
        
        elif data_type == 'cartera':
            for index, row in df.iterrows():
                cur.execute('''
                    INSERT INTO cartera (numero_factura, cliente, monto_adeudado, dias_vencido, estado)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (row.get('numero_factura'), row['cliente'], row['monto_adeudado'], row.get('dias_vencido'), row.get('estado', 'vigente')))
                records_inserted += 1
        
        elif data_type == 'productos':
            for index, row in df.iterrows():
                cur.execute('''
                    INSERT INTO productos (id_producto, nombre, cantidad_vendida, precio_unitario, fecha)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id_producto) DO UPDATE SET
                        cantidad_vendida = EXCLUDED.cantidad_vendida,
                        precio_unitario = EXCLUDED.precio_unitario,
                        fecha = EXCLUDED.fecha
                ''', (row['id_producto'], row['nombre'], row['cantidad_vendida'], row['precio_unitario'], row['fecha']))
                records_inserted += 1
        
        elif data_type == 'gastos':
            for index, row in df.iterrows():
                cur.execute('''
                    INSERT INTO gastos (fecha, categoria, descripcion, monto, area)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (row['fecha'], row['categoria'], row['descripcion'], row['monto'], row['area']))
                records_inserted += 1
        
        conn.commit()
        
        # Registrar carga
        cur.execute('''
            INSERT INTO cargas_archivos (nombre_archivo, tipo_datos, registros, estado)
            VALUES (%s, %s, %s, %s)
        ''', (filepath, data_type, records_inserted, 'exitoso'))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Procesados {records_inserted} registros de {data_type}")
        return {'records_inserted': records_inserted}
        
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        logger.error(f"Error procesando Excel: {e}")
        raise

@app.route('/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Total facturas
        cur.execute('SELECT COUNT(*) as total, COALESCE(SUM(monto), 0) as monto_total FROM facturas')
        facturas = cur.fetchone()
        
        # Cartera vencida
        cur.execute('SELECT COUNT(*) as vencidas, COALESCE(SUM(monto_adeudado), 0) as monto_vencido FROM cartera WHERE dias_vencido > 0')
        cartera = cur.fetchone()
        
        # Productos
        cur.execute('SELECT COUNT(DISTINCT id_producto) as total FROM productos')
        productos = cur.fetchone()
        
        # Gastos
        cur.execute('SELECT COUNT(*) as total, COALESCE(SUM(monto), 0) as total_monto FROM gastos')
        gastos = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'facturas': dict(facturas) if facturas else {'total': 0, 'monto_total': 0},
            'cartera_vencida': dict(cartera) if cartera else {'vencidas': 0, 'monto_vencido': 0},
            'productos': dict(productos) if productos else {'total': 0},
            'gastos': dict(gastos) if gastos else {'total': 0, 'total_monto': 0}
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/templates', methods=['GET'])
def get_templates():
    """Listar plantillas disponibles y sus estructuras"""
    templates_info = {}
    for data_type, model in DATA_MODELS.items():
        templates_info[data_type] = {
            'required_columns': model['required_columns'],
            'optional_columns': model['optional_columns'],
            'table': model['table']
        }
    return jsonify(templates_info), 200

@app.route('/validate', methods=['POST'])
def validate_file():
    """Validar estructura de archivo sin guardarlo"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        data_type = request.form.get('type', 'facturas')
        
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': 'Solo archivos .xlsx permitidos'}), 400
        
        # Leer sin guardar
        df = pd.read_excel(file)
        
        # Validar
        validation = validate_excel_structure(df, data_type)
        
        if validation['valid']:
            return jsonify({
                'valid': True,
                'message': 'Estructura correcta',
                'rows': len(df),
                'columns': df.columns.tolist()
            }), 200
        else:
            return jsonify(validation), 400
            
    except Exception as e:
        logger.error(f"Error validando archivo: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=True)
