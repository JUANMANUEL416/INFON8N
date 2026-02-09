"""
Verificar qué reportes tienen datos disponibles
"""
import requests

BASE_URL = "http://localhost:5000"

session = requests.Session()
session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': 'admin123'})

# Obtener reportes
response = session.get(f"{BASE_URL}/api/reportes/disponibles")
reportes = response.json()

print("\n📊 Verificando datos en reportes:\n")

for reporte in reportes:
    codigo = reporte['codigo']
    nombre = reporte['nombre']
    
    # Consultar datos
    response = session.get(f"{BASE_URL}/api/reportes/{codigo}/datos")
    
    if response.status_code == 200:
        datos = response.json()
        total = len(datos)
        print(f"{'✅' if total > 0 else '❌'} {codigo:30} - {total:4} registros")
    else:
        print(f"⚠️  {codigo:30} - Error al consultar")

print()
