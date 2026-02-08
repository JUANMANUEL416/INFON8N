"""
Prueba rápida del endpoint de informe personalizado
"""
import requests
import time

print("🔍 Probando endpoint de informe personalizado...\n")

# Esperar a que el backend esté listo
print("⏳ Esperando 5 segundos a que backend inicie...")
time.sleep(5)

# Probar health check
try:
    health = requests.get("http://localhost:5000/health", timeout=5)
    if health.status_code == 200:
        print("✅ Backend está funcionando\n")
    else:
        print(f"⚠️ Backend responde pero con código {health.status_code}\n")
except Exception as e:
    print(f"❌ Backend no responde: {e}\n")
    exit(1)

# Obtener reportes
print("📋 Obteniendo reportes disponibles...")
reportes_resp = requests.get("http://localhost:5000/api/admin/reportes", timeout=5)

if reportes_resp.status_code != 200:
    print(f"❌ Error obteniendo reportes: {reportes_resp.status_code}")
    exit(1)

reportes = reportes_resp.json()
if not reportes:
    print("❌ No hay reportes disponibles")
    exit(1)

print(f"✅ {len(reportes)} reporte(s) encontrado(s)\n")

# Usar el reporte con más datos
codigo_reporte = "facturacion emitida de manera unitaria"

print(f"📊 Usando reporte: {codigo_reporte}\n")

# Probar el endpoint de informe personalizado
print("🤖 Generando informe personalizado...")
print("   Solicitud: 'top 5 terceros con mayor facturación'\n")

payload = {
    "solicitud": "top 5 terceros con mayor facturación",
    "exportar_excel": False,
    "enviar_correo": False
}

try:
    response = requests.post(
        f"http://localhost:5000/api/analysis/{codigo_reporte}/informe-personalizado",
        json=payload,
        timeout=90
    )
    
    print(f"📡 Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        resultado = response.json()
        
        if resultado.get('success'):
            print("✅ ¡INFORME GENERADO EXITOSAMENTE!\n")
            
            informe = resultado['informe']
            
            print("=" * 70)
            print(f"📊 Reporte: {informe['reporte']}")
            print(f"📝 Solicitud: {informe['solicitud']}")
            print(f"📈 Total registros: {informe['total_registros']:,}")
            print(f"📊 Registros procesados: {informe['registros_procesados']}")
            print("=" * 70)
            
            if informe.get('graficos'):
                print(f"\n📈 Gráficos generados: {len(informe['graficos'])}")
                for idx, grafico in enumerate(informe['graficos'], 1):
                    print(f"   {idx}. {grafico['titulo']} ({grafico['tipo']})")
            
            if informe.get('estadisticas'):
                print(f"\n📊 Estadísticas disponibles:")
                for tipo in informe['estadisticas'].keys():
                    print(f"   - {tipo}")
            
            if informe.get('resumen_ejecutivo'):
                print(f"\n📝 Resumen Ejecutivo (primeras 200 caracteres):")
                print(f"   {informe['resumen_ejecutivo'][:200]}...")
            
            if informe.get('datos_procesados'):
                print(f"\n📋 Top 5 Resultados:")
                for idx, dato in enumerate(informe['datos_procesados'][:5], 1):
                    print(f"   {idx}. {dato}")
            
            print("\n" + "=" * 70)
            print("✅ EL SISTEMA DE INFORMES CON IA ESTÁ FUNCIONANDO")
            print("=" * 70)
            
            print("\n💡 Próximos pasos:")
            print("   1. Probar con exportar_excel=True para descargar Excel")
            print("   2. Configurar correo y probar enviar_correo=True")
            print("   3. Probar otras solicitudes personalizadas")
            
        else:
            print(f"❌ Error en el informe: {resultado.get('error', 'Desconocido')}")
    
    elif response.status_code == 404:
        print("❌ Endpoint no encontrado (404)")
        print("⚠️ El endpoint '/api/analysis/<codigo>/informe-personalizado' no está registrado")
        print("\n🔧 Solución:")
        print("   1. Verificar que app.py tenga el endpoint definido")
        print("   2. Reiniciar el backend: docker-compose restart backend")
    
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print("⏱️ Timeout: La generación tardó más de 90 segundos")
    print("💡 Esto es normal si hay muchos datos o la IA está procesando")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
