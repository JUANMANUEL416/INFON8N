"""
Script simple para probar el informe personalizado con IA
"""
import requests
import json

BASE_URL = "http://localhost:5000"

# Usar el reporte que sabemos que tiene datos
CODIGO_REPORTE = "facturacion emitida de manera unitaria"

print("=" * 80)
print(f"🤖 GENERANDO INFORME PERSONALIZADO")
print("=" * 80)
print(f"\n📊 Reporte: {CODIGO_REPORTE}")
print(f"📝 Solicitud: 'facturación semanal agrupada por tercero'\n")

# Generar informe personalizado
payload = {
    "solicitud": "facturación semanal agrupada por tercero con análisis de top clientes",
    "exportar_excel": False,  # Primero solo JSON
    "enviar_correo": False
}

print("⏳ Generando informe (esto puede tomar 30-60 segundos)...\n")

try:
    response = requests.post(
        f"{BASE_URL}/api/analysis/{CODIGO_REPORTE}/informe-personalizado",
        json=payload,
        timeout=120
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        resultado = response.json()
        
        if resultado.get('success'):
            informe = resultado['informe']
            
            print("\n✅ ¡INFORME GENERADO EXITOSAMENTE!\n")
            print("=" * 80)
            print(f"📊 REPORTE: {informe['reporte']}")
            print(f"📝 SOLICITUD: {informe['solicitud']}")
            print(f"📅 FECHA: {informe['fecha_generacion']}")
            print("=" * 80)
            
            print(f"\n📈 ESTADÍSTICAS:")
            print(f"   Total registros original: {informe['total_registros']:,}")
            print(f"   Registros procesados: {informe['registros_procesados']:,}")
            
            if informe.get('agrupaciones'):
                print(f"\n📋 AGRUPACIONES APLICADAS:")
                agrup = informe['agrupaciones']
                for key, value in agrup.items():
                    print(f"   {key}: {value}")
            
            if informe.get('estadisticas'):
                print(f"\n📊 ESTADÍSTICAS CALCULADAS:")
                stats = informe['estadisticas']
                
                if stats.get('total'):
                    print(f"\n   TOTALES:")
                    for campo, valor in list(stats['total'].items())[:5]:
                        print(f"      {campo}: {valor:,.2f}")
                
                if stats.get('promedio'):
                    print(f"\n   PROMEDIOS:")
                    for campo, valor in list(stats['promedio'].items())[:5]:
                        print(f"      {campo}: {valor:,.2f}")
            
            if informe.get('graficos'):
                print(f"\n📈 GRÁFICOS GENERADOS: {len(informe['graficos'])}")
                for idx, grafico in enumerate(informe['graficos'], 1):
                    print(f"   {idx}. {grafico['titulo']} ({grafico['tipo']})")
                    print(f"      Elementos: {len(grafico['labels'])}")
                    if len(grafico['labels']) <= 5:
                        for label, dato in zip(grafico['labels'], grafico['datos']):
                            print(f"         - {label}: {dato:,.2f}")
            
            if informe.get('resumen_ejecutivo'):
                print(f"\n📝 RESUMEN EJECUTIVO:")
                print("=" * 80)
                print(informe['resumen_ejecutivo'])
                print("=" * 80)
            
            if informe.get('datos_procesados'):
                print(f"\n📋 DATOS PROCESADOS (TOP 10):")
                for idx, dato in enumerate(informe['datos_procesados'][:10], 1):
                    print(f"   {idx}. {dato}")
            
            print("\n" + "=" * 80)
            print("✅ LA IA PUEDE GENERAR INFORMES PERSONALIZADOS")
            print("=" * 80)
            
            print("\n💡 Ahora puedes:")
            print("   1. Exportar a Excel con gráficos incrustados (exportar_excel: true)")
            print("   2. Enviar por correo con adjuntos (enviar_correo: true)")
            print("   3. Hacer otras solicitudes personalizadas")
            
            print("\n📧 Para probar con Excel y correo, modifica el payload:")
            print('''
payload = {
    "solicitud": "tu solicitud aquí",
    "exportar_excel": True,
    "enviar_correo": True,
    "destinatarios": ["tu@email.com"]
}
''')
            
        else:
            print(f"\n❌ Error: {resultado.get('error', 'Desconocido')}")
    
    else:
        print(f"\n❌ Error HTTP {response.status_code}:")
        print(response.text)

except requests.exceptions.Timeout:
    print("\n⏱️ Timeout: La solicitud tardó más de 120 segundos")
    print("💡 Intenta con un reporte con menos datos o aumenta el timeout")
    
except requests.exceptions.ConnectionError:
    print(f"\n❌ Error de conexión: No se puede conectar a {BASE_URL}")
    print("💡 Verifica que el backend esté corriendo: docker-compose ps")
    
except Exception as e:
    print(f"\n❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()

print()
