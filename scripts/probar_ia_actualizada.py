"""
Prueba: Verificar que GPT-4 conoce sus capacidades
"""
import requests
import json

print("🤖 Probando que la IA conoce sus capacidades de gráficos y Excel\n")
print("=" * 80)

# Test 1: Pregunta sobre capacidad de generar gráficos
print("\n📊 Test 1: ¿Puedes generar gráficos?")
print("-" * 80)

response = requests.post(
    "http://localhost:5000/api/analysis/facturacion%20emitida%20de%20manera%20unitaria/pregunta",
    json={"pregunta": "¿Puedes generar gráficos y exportar a Excel?"},
    timeout=30
)

if response.status_code == 200:
    data = response.json()
    print(f"\n🤖 Respuesta de la IA:\n{data['respuesta']}\n")
    
    if any(palabra in data['respuesta'].lower() for palabra in ['sí', 'si', 'puedo', 'capaz', 'generar']):
        print("✅ CORRECTO: La IA confirma que PUEDE generar gráficos")
    elif any(palabra in data['respuesta'].lower() for palabra in ['no puedo', 'no tengo', 'no tengo la capacidad']):
        print("❌ ERROR: La IA dice que NO PUEDE (esto es incorrecto)")
    else:
        print("⚠️ AMBIGUO: La respuesta no es clara")
else:
    print(f"❌ Error HTTP {response.status_code}")

# Test 2: Solicitud de informe con gráfico
print("\n\n📈 Test 2: Solicitar informe con gráfico")
print("-" * 80)

response = requests.post(
    "http://localhost:5000/api/analysis/facturacion%20emitida%20de%20manera%20unitaria/informe-personalizado",
    json={
        "solicitud": "muéstrame los 5 principales terceros con gráfico de barras",
        "exportar_excel": False
    },
    timeout=60
)

if response.status_code == 200:
    data = response.json()
    informe = data.get('informe', {})
    
    print(f"✅ Informe generado")
    print(f"   Registros procesados: {informe.get('registros_procesados', 'N/A')}")
    print(f"   Gráficos generados: {len(informe.get('graficos', []))}")
    
    if informe.get('graficos'):
        print(f"\n   📊 Detalles del gráfico:")
        grafico = informe['graficos'][0]
        print(f"      Tipo: {grafico.get('tipo')}")
        print(f"      Título: {grafico.get('titulo')}")
        print(f"      Datos: {len(grafico.get('datos', []))} puntos")
        print("\n   ✅ CONFIRMADO: Sistema genera gráficos correctamente")
    else:
        print("   ⚠️ No se generaron gráficos")
        
    if informe.get('resumen_ejecutivo'):
        print(f"\n   📝 Resumen ejecutivo generado:")
        print(f"   {informe['resumen_ejecutivo'][:200]}...")
else:
    print(f"❌ Error HTTP {response.status_code}")

print("\n\n" + "=" * 80)
print("📋 CONCLUSIÓN")
print("=" * 80)
print("""
Si ves:
✅ "La IA confirma que PUEDE generar gráficos" → Prompts actualizados correctamente
✅ "Sistema genera gráficos correctamente" → Funcionalidad operativa

Si ves errores:
❌ "La IA dice que NO PUEDE" → Reiniciar backend con: docker-compose restart backend
❌ "No se generaron gráficos" → Verificar logs con: docker logs devprueba-backend
""")
