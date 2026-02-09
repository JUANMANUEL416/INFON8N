"""
Debug: Ver qué datos retorna el endpoint del gráfico
"""
import requests
import json

BASE_URL = "http://localhost:5000"

session = requests.Session()
session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': 'admin123'})

codigo = "facturacion emitida de manera unitaria"
pregunta = "hazme un gráfico con los 5 tipos de tercero a los que más se les facturó"

response = session.post(
    f"{BASE_URL}/api/analysis/{codigo}/pregunta",
    json={'pregunta': pregunta}
)

print("\n" + "="*70)
print("DEBUG: Respuesta del Backend")
print("="*70)
print(f"\nStatus Code: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")

if 'application/json' in response.headers.get('content-type', ''):
    data = response.json()
    print(f"\nDATOS RETORNADOS:")
    print(json.dumps(data, indent=2, ensure_ascii=True))
    
    if 'grafico' in data:
        print("\nObjeto 'grafico' encontrado:")
        grafico = data['grafico']
        print(f"  - tipo: {grafico.get('tipo')}")
        print(f"  - titulo: {grafico.get('titulo')}")
        print(f"  - labels: {grafico.get('labels')}")
        print(f"  - datos: {grafico.get('datos')}")
        print(f"  - columna: {grafico.get('columna')}")
    else:
        print("\nNO hay objeto 'grafico' en la respuesta")
else:
    print("\nNo es JSON, es un archivo")
    print(f"Tamano: {len(response.content)} bytes")

print()
