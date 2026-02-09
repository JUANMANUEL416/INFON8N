"""
Script para verificar el estado completo de ChromaDB
"""
import requests
import sys

print("🔍 Verificando ChromaDB...")
print("=" * 60)

# 1. Verificar API de ChromaDB
print("\n1️⃣ Verificando API de ChromaDB...")
try:
    response = requests.get("http://localhost:8000/api/v2", timeout=5)
    if response.status_code == 200:
        print("   ✅ ChromaDB responde correctamente")
        print(f"   📡 Heartbeat: {response.json()}")
    else:
        print(f"   ⚠️ ChromaDB responde con código {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# 2. Verificar Backend
print("\n2️⃣ Verificando Backend...")
try:
    response = requests.get("http://localhost:5000/health", timeout=5)
    if response.status_code == 200:
        print("   ✅ Backend funcionando")
    else:
        print(f"   ⚠️ Backend responde con código {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# 3. Verificar modelo descargado
print("\n3️⃣ Verificando descarga del modelo de embeddings...")
print("   (Revisar logs del backend para ver progreso)")
print()
print("   Ejecutar: docker logs devprueba-backend --tail 10")
print()
print("   Buscar línea que diga:")
print("   '/root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz: 100%'")
print()

# 4. Listar colecciones existentes
print("\n4️⃣ Colecciones en ChromaDB...")
try:
    # Intentar listar colecciones vía backend
    response = requests.get("http://localhost:5000/api/admin/reportes", timeout=5)
    if response.status_code == 200:
        reportes = response.json()
        print(f"   ℹ️ Reportes disponibles: {len(reportes)}")
        for r in reportes[:3]:  # Mostrar primeros 3
            print(f"      - {r.get('codigo', 'N/A')}")
    
    print("\n   💡 Para indexar un reporte:")
    print("      POST http://localhost:5000/api/analysis/{codigo}/indexar")
    
except Exception as e:
    print(f"   ⚠️ No se pudieron listar reportes: {e}")

print("\n" + "=" * 60)
print("✅ Verificación completada")
print()
print("📝 SIGUIENTE PASO:")
print("   1. Esperar a que termine descarga del modelo (si está en progreso)")
print("   2. Ejecutar: python .\\scripts\\test_indexacion.py")
print("   3. La primera indexación tardará ~1 min, las siguientes <10 seg")
print()
