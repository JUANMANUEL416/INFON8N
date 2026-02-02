from flask import Flask, request, jsonify
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
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Base de datos inicializada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error inicializando BD: {e}")
        return False

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

def process_excel(filepath, data_type):
    """Procesar archivo Excel e insertar en BD"""
    df = pd.read_excel(filepath)
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
        cur.execute('SELECT COUNT(*) as total, SUM(monto) as monto_total FROM facturas')
        facturas = cur.fetchone()
        
        # Cartera vencida
        cur.execute('SELECT COUNT(*) as vencidas, SUM(monto_adeudado) as monto_vencido FROM cartera WHERE dias_vencido > 0')
        cartera = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'facturas': dict(facturas),
            'cartera_vencida': dict(cartera)
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=True)
