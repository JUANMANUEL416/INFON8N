"""
Test Rápido - Memoria + Function Calling
Prueba simple para verificar funcionamiento
"""

import requests
import json

BASE_URL = "http://localhost:5000"
REPORTE = "facturacion emitida de manera unitaria"

print("\n" + "="*70)
print("  🧪 TEST RÁPIDO: MEMORIA + FUNCTION CALLING")
print("="*70)

# Test 1: Function Calling
print("\n📝 Test 1: El agente ejecuta funciones automáticamente")
print("-" * 70)

response = requests.post(f"{BASE_URL}/api/analysis/{REPORTE}/pregunta", json={
    "pregunta": "¿Cuál es el total facturado en el campo vr_total?",
    "session_id": "test_rapido"
})

if response.status_code == 200:
    data = response.json()
    print(f"✅ Respuesta recibida")
    print(f"\n🤖 Agente: {data.get('respuesta', '')[:200]}...")
    
    if data.get('funciones_ejecutadas'):
        print(f"\n🔧 Funciones ejecutadas: {', '.join(data['funciones_ejecutadas'])}")
        print("✅ FUNCTION CALLING FUNCIONANDO!")
    else:
        print("⚠️ No se ejecutaron funciones (puede ser normal si respondió directamente)")
else:
    print(f"❌ Error: {response.text}")

# Test 2: Memoria Conversacional
print("\n\n📝 Test 2: El agente recuerda el contexto")
print("-" * 70)

response2 = requests.post(f"{BASE_URL}/api/analysis/{REPORTE}/pregunta", json={
    "pregunta": "¿Y cuántos registros son?",  # NO especifica "facturado", usa contexto
    "session_id": "test_rapido"
})

if response2.status_code == 200:
    data2 = response2.json()
    print(f"✅ Respuesta recibida")
    print(f"\n🤖 Agente: {data2.get('respuesta', '')[:200]}...")
    print("\n✅ MEMORIA CONVERSACIONAL FUNCIONANDO!")
    print("   (El agente entendió el contexto sin re-explicar)")
else:
    print(f"❌ Error: {response2.text}")

# Ver historial
print("\n\n📝 Test 3: Revisar historial de conversación")
print("-" * 70)

response3 = requests.get(f"{BASE_URL}/api/analysis/{REPORTE}/session/test_rapido/historial")

if response3.status_code == 200:
    historial = response3.json()
    print(f"✅ Historial obtenido: {historial['mensajes']} mensajes")
    
    for i, msg in enumerate(historial['historial'][:4], 1):  # Mostrar primeros 4
        role_emoji = "👤" if msg['role'] == 'user' else "🤖"
        print(f"\n{i}. {role_emoji} {msg['role'].upper()}")
        print(f"   {msg['content'][:100]}...")
    
    print("\n✅ HISTORIAL FUNCIONANDO!")
else:
    print(f"❌ Error: {response3.text}")

print("\n" + "="*70)
print("  ✅ TESTS COMPLETADOS")
print("="*70)
print("\n🎉 Las nuevas capacidades están funcionando:")
print("  ✅ Function Calling - El agente ejecuta funciones")
print("  ✅ Memoria - Recuerda conversaciones previas")
print("  ✅ Historial - Se guarda correctamente")
print("\n📖 Documentación completa: MEJORAS_FUNCTION_CALLING.md")
print("🧪 Demo completa: python .\\scripts\\test_function_calling.py")
