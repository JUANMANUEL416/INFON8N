"""
Prueba de indexación de datos en ChromaDB
"""
import requests
import time

print("🔍 Probando indexación de datos en ChromaDB\n")

# Esperar a que ChromaDB esté listo
print("⏳ Esperando 15 segundos a que ChromaDB esté completamente iniciado...")
time.sleep(15)

# Verificar que el backend esté funcionando
print("\n1️⃣ Verificando backend...")
try:
    health = requests.get("http://localhost:5000/health", timeout=5)
    if health.status_code == 200:
        print("   ✅ Backend funcionando")
    else:
        print(f"   ⚠️ Backend responde con código {health.status_code}")
        exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Obtener un reporte
print("\n2️⃣ Obteniendo reporte...")
reportes = requests.get("http://localhost:5000/api/admin/reportes", timeout=5).json()
codigo_reporte = "facturacion emitida de manera unitaria"
print(f"   ✅ Usando reporte: {codigo_reporte}")

# Probar indexación
print("\n3️⃣ Probando indexación de datos...")
print("   (Esto puede tardar 20-30 segundos)")

try:
    response = requests.post(
        f"http://localhost:5000/api/analysis/{codigo_reporte}/indexar",
        timeout=180
    )
    
    print(f"\n📡 Status: {response.status_code}")
    
    if response.status_code == 200:
        resultado = response.json()
        print("\n✅ ¡INDEXACIÓN EXITOSA!")
        print(f"   Registros indexados: {resultado.get('indexed', 'N/A')}")
        print(f"   Colección: {resultado.get('collection', 'N/A')}")
        print("\n🎉 ChromaDB está funcionando correctamente")
        
    else:
        print(f"\n❌ Error en indexación:")
        print(response.text)
        
        if "ChromaDB no disponible" in response.text:
            print("\n💡 SOLUCIÓN:")
            print("   1. Verificar que ChromaDB esté corriendo:")
            print("      docker-compose ps chroma")
            print("   2. Reiniciar ChromaDB:")
            print("      docker-compose restart chroma")
            print("   3. Esperar 20-30 segundos y volver a intentar")

except requests.exceptions.Timeout:
    print("\n⏱️ Timeout: La indexación tardó más de 60 segundos")
    print("   Esto puede ser normal con muchos datos")
    
except Exception as e:
    print(f"\n❌ Error: {e}")

print()
