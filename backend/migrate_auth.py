"""
Script de migración para agregar el sistema de autenticación con grupos y permisos
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de base de datos
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': os.getenv('DB_PORT', 5432),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123'),
    'database': os.getenv('DB_NAME', 'informes_db')
}

def migrar_autenticacion():
    """Migrar sistema de autenticación"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        print("🔄 Iniciando migración de autenticación...")
        
        # 1. Crear tabla de grupos
        print("📋 Creando tabla de grupos...")
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
        
        # 2. Insertar grupos por defecto
        print("👥 Insertando grupos por defecto...")
        cur.execute('''
            INSERT INTO grupos (codigo, nombre, descripcion, estado)
            VALUES ('admin', 'Administradores', 'Grupo con acceso total al sistema', 'activo')
            ON CONFLICT (codigo) DO NOTHING
            RETURNING id;
        ''')
        
        result = cur.fetchone()
        if result:
            grupo_admin_id = result[0]
            print(f"   ✅ Grupo admin creado con ID: {grupo_admin_id}")
        else:
            cur.execute("SELECT id FROM grupos WHERE codigo = 'admin'")
            grupo_admin_id = cur.fetchone()[0]
            print(f"   ℹ️  Grupo admin ya existe con ID: {grupo_admin_id}")
        
        cur.execute('''
            INSERT INTO grupos (codigo, nombre, descripcion, estado)
            VALUES ('usuarios', 'Usuarios Generales', 'Grupo con permisos básicos de visualización', 'activo')
            ON CONFLICT (codigo) DO NOTHING
            RETURNING id;
        ''')
        
        result = cur.fetchone()
        if result:
            grupo_usuarios_id = result[0]
            print(f"   ✅ Grupo usuarios creado con ID: {grupo_usuarios_id}")
        else:
            cur.execute("SELECT id FROM grupos WHERE codigo = 'usuarios'")
            grupo_usuarios_id = cur.fetchone()[0]
            print(f"   ℹ️  Grupo usuarios ya existe con ID: {grupo_usuarios_id}")
        
        # 3. Renombrar tabla usuarios antigua si existe
        print("🔧 Actualizando tabla usuarios...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' AND column_name = 'password'
        """)
        
        if not cur.fetchone():
            print("   📝 Agregando campo password a usuarios...")
            cur.execute("ALTER TABLE usuarios RENAME TO usuarios_old")
            
            # Crear nueva tabla usuarios
            cur.execute('''
                CREATE TABLE usuarios (
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
            
            # Migrar datos existentes
            cur.execute(f"""
                INSERT INTO usuarios (username, password, nombre, estado, grupo_id, created_at)
                SELECT 
                    username, 
                    'admin123' as password,
                    COALESCE(nombre_completo, username) as nombre,
                    CASE WHEN activo THEN 'activo' ELSE 'inactivo' END as estado,
                    {grupo_admin_id} as grupo_id,
                    created_at
                FROM usuarios_old
                ON CONFLICT (username) DO NOTHING
            """)
            
            print(f"   ✅ Datos migrados de usuarios_old a usuarios")
        else:
            print("   ℹ️  La tabla usuarios ya tiene el campo password")
        
        # 4. Insertar usuario admin si no existe
        print("👤 Verificando usuario admin...")
        cur.execute('''
            INSERT INTO usuarios (username, password, nombre, estado, grupo_id)
            VALUES ('admin', 'admin123', 'Administrador del Sistema', 'activo', %s)
            ON CONFLICT (username) 
            DO UPDATE SET 
                password = EXCLUDED.password,
                grupo_id = EXCLUDED.grupo_id,
                estado = 'activo'
            RETURNING id;
        ''', (grupo_admin_id,))
        
        admin_id = cur.fetchone()[0]
        print(f"   ✅ Usuario admin configurado con ID: {admin_id}")
        
        # 5. Crear tabla intermedia grupos_reportes
        print("🔐 Creando tabla de permisos grupos_reportes...")
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
        print("   ✅ Tabla grupos_reportes creada")
        
        # 6. Asignar todos los permisos al grupo admin
        print("🔑 Asignando permisos al grupo admin...")
        cur.execute('''
            SELECT codigo FROM reportes_config WHERE activo = TRUE
        ''')
        
        reportes = cur.fetchall()
        permisos_asignados = 0
        
        for (reporte_codigo,) in reportes:
            cur.execute('''
                INSERT INTO grupos_reportes 
                (grupo_id, reporte_codigo, puede_ver, puede_crear, puede_editar, puede_eliminar)
                VALUES (%s, %s, TRUE, TRUE, TRUE, TRUE)
                ON CONFLICT (grupo_id, reporte_codigo) DO NOTHING
            ''', (grupo_admin_id, reporte_codigo))
            
            if cur.rowcount > 0:
                permisos_asignados += 1
        
        print(f"   ✅ {permisos_asignados} permisos asignados al grupo admin")
        
        conn.commit()
        print("\n✅ ¡Migración completada exitosamente!")
        print(f"\n📊 Resumen:")
        print(f"   - Grupo Admin ID: {grupo_admin_id}")
        print(f"   - Grupo Usuarios ID: {grupo_usuarios_id}")
        print(f"   - Usuario admin ID: {admin_id}")
        print(f"   - Permisos asignados: {permisos_asignados}")
        print(f"\n🔐 Credenciales de acceso:")
        print(f"   Usuario: admin")
        print(f"   Password: admin123")
        
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
    migrar_autenticacion()
