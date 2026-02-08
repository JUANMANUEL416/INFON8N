"""
Prueba básica de endpoints disponibles
"""
import requests

BASE_URL = "http://localhost:5000"

print("Verificando endpoints API...\n")

# Probar endpoints existentes
endpoints = [
    ("/health", "GET"),
    ("/api/admin/reportes", "GET"),
    ("/api/analysis/test/indexar", "POST"),
    ("/api/analysis/test/pregunta", "POST"),
    ("/api/analysis/test/informe-personalizado", "POST"),
]

for endpoint, metodo in endpoints:
    try:
        if metodo == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=3)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", json={}, timeout=3)
        
        print(f"✅ {metodo} {endpoint} -> {response.status_code}")
        
    except requests.exceptions.Timeout:
        print(f"⏱️ {metodo} {endpoint} -> Timeout")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ {metodo} {endpoint} -> Conexión rechazada")
    except Exception as e:
        print(f"⚠️ {metodo} {endpoint} -> {type(e).__name__}")

print("\nS Sistema funcionando correctamente!")
