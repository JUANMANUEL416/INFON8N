"""
Script de migración para agregar campos de API y consulta a reportes
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': os.getenv('DB_PORT', 5432),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123'),
    'database': os.getenv('DB_NAME', 'informes_db')
}

def migrar_api_consulta():
    """Agregar campos de API y consulta"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        print("🔄 Agregando campos de API y consulta a reportes_config...")
        
        # Verificar si las columnas ya existen
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'reportes_config' AND column_name = 'api_endpoint'
        """)
        
        if not cur.fetchone():
            print("   📝 Agregando columna api_endpoint...")
            cur.execute("ALTER TABLE reportes_config ADD COLUMN api_endpoint VARCHAR(255)")
            print("   ✅ Columna api_endpoint agregada")
        else:
            print("   ℹ️  Columna api_endpoint ya existe")
        
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'reportes_config' AND column_name = 'query_template'
        """)
        
        if not cur.fetchone():
            print("   📝 Agregando columna query_template...")
            cur.execute("ALTER TABLE reportes_config ADD COLUMN query_template TEXT")
            print("   ✅ Columna query_template agregada")
        else:
            print("   ℹ️  Columna query_template ya existe")
        
        conn.commit()
        print("\n✅ ¡Migración completada exitosamente!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    migrar_api_consulta()
