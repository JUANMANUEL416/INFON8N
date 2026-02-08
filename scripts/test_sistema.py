"""
Script de pruebas del sistema de autenticación y API
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_login():
    """Probar login"""
    print("\n🔐 Probando Login...")
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Login exitoso: {data['message']}")
        print(f"   Usuario: {data['usuario']['nombre']}")
        print(f"   Grupo: {data['usuario']['grupo_nombre']}")
        return data['usuario']
    else:
        print(f"❌ Login falló: {response.json()}")
        return None

def test_listar_usuarios():
    """Probar listar usuarios"""
    print("\n👥 Probando listar usuarios...")
    response = requests.get(f"{BASE_URL}/api/usuarios")
    
    if response.status_code == 200:
        usuarios = response.json()
        print(f"✅ Encontrados {len(usuarios)} usuarios:")
        for u in usuarios:
            print(f"   - {u['username']}: {u['nombre']} ({u['grupo_nombre']})")
        return usuarios
    else:
        print(f"❌ Error: {response.status_code}")
        return []

def test_listar_grupos():
    """Probar listar grupos"""
    print("\n📋 Probando listar grupos...")
    response = requests.get(f"{BASE_URL}/api/grupos")
    
    if response.status_code == 200:
        grupos = response.json()
        print(f"✅ Encontrados {len(grupos)} grupos:")
        for g in grupos:
            print(f"   - {g['codigo']}: {g['nombre']} ({g['total_usuarios']} usuarios)")
        return grupos
    else:
        print(f"❌ Error: {response.status_code}")
        return []

def test_crear_grupo():
    """Probar crear grupo"""
    print("\n➕ Probando crear grupo...")
    response = requests.post(f"{BASE_URL}/api/grupos", json={
        "codigo": "ventas_test",
        "nombre": "Equipo de Ventas Test",
        "descripcion": "Grupo de prueba para ventas",
        "estado": "activo"
    })
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ Grupo creado: {data['message']}")
        return data['grupo_id']
    else:
        print(f"⚠️  {response.json()}")
        return None

def test_crear_usuario():
    """Probar crear usuario"""
    print("\n➕ Probando crear usuario...")
    
    # Primero obtener un grupo
    grupos = requests.get(f"{BASE_URL}/api/grupos").json()
    if not grupos:
        print("❌ No hay grupos disponibles")
        return None
    
    grupo_id = grupos[0]['id']
    
    response = requests.post(f"{BASE_URL}/api/usuarios", json={
        "username": "usuario_test",
        "password": "test123",
        "nombre": "Usuario de Prueba",
        "grupo_id": grupo_id,
        "estado": "activo"
    })
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ Usuario creado: {data['message']}")
        return data['user_id']
    else:
        print(f"⚠️  {response.json()}")
        return None

def test_listar_reportes():
    """Probar listar reportes"""
    print("\n📊 Probando listar reportes...")
    response = requests.get(f"{BASE_URL}/api/admin/reportes")
    
    if response.status_code == 200:
        reportes = response.json()
        print(f"✅ Encontrados {len(reportes)} reportes:")
        for r in reportes:
            print(f"   - {r['codigo']}: {r['nombre']}")
            if r.get('api_endpoint'):
                print(f"     API: {r['api_endpoint']}")
        return reportes
    else:
        print(f"❌ Error: {response.status_code}")
        return []

def test_consultar_datos():
    """Probar consultar datos de un reporte"""
    print("\n🔍 Probando consulta de datos...")
    
    # Obtener un reporte
    reportes = requests.get(f"{BASE_URL}/api/admin/reportes").json()
    if not reportes:
        print("⚠️  No hay reportes disponibles")
        return
    
    codigo = reportes[0]['codigo']
    print(f"   Consultando reporte: {codigo}")
    
    response = requests.get(f"{BASE_URL}/api/query/{codigo}?limite=5")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Consulta exitosa:")
        print(f"   Reporte: {data['reporte']}")
        print(f"   Total registros: {data['total']}")
        if data['datos']:
            print(f"   Primer registro: {data['datos'][0]['datos']}")
    else:
        print(f"❌ Error: {response.json()}")

def test_permisos():
    """Probar sistema de permisos"""
    print("\n🔐 Probando sistema de permisos...")
    
    # Obtener un grupo
    grupos = requests.get(f"{BASE_URL}/api/grupos").json()
    if not grupos or len(grupos) < 2:
        print("⚠️  No hay suficientes grupos")
        return
    
    grupo_id = grupos[1]['id']  # Usar segundo grupo (no admin)
    
    # Listar permisos actuales
    response = requests.get(f"{BASE_URL}/api/permisos/grupo/{grupo_id}")
    permisos = response.json()
    print(f"✅ Permisos actuales del grupo {grupo_id}: {len(permisos)}")
    
    # Asignar un permiso
    reportes = requests.get(f"{BASE_URL}/api/admin/reportes").json()
    if reportes:
        codigo = reportes[0]['codigo']
        response = requests.post(
            f"{BASE_URL}/api/permisos/grupo/{grupo_id}/reporte/{codigo}",
            json={
                "puede_ver": True,
                "puede_crear": False,
                "puede_editar": False,
                "puede_eliminar": False
            }
        )
        if response.status_code == 200:
            print(f"✅ Permiso de lectura asignado para {codigo}")

def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("="*60)
    print("🧪 INICIANDO PRUEBAS DEL SISTEMA")
    print("="*60)
    
    try:
        # Test 1: Login
        usuario = test_login()
        
        # Test 2: Usuarios
        test_listar_usuarios()
        #test_crear_usuario()
        
        # Test 3: Grupos
        test_listar_grupos()
        #test_crear_grupo()
        
        # Test 4: Reportes
        test_listar_reportes()
        
        # Test 5: Consultas
        test_consultar_datos()
        
        # Test 6: Permisos
        test_permisos()
        
        print("\n" + "="*60)
        print("✅ PRUEBAS COMPLETADAS")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error de conexión. ¿El servidor está corriendo?")
        print("   Ejecuta: docker-compose up -d")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_all_tests()
