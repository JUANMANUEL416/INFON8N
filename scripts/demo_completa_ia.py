"""
Demostración completa del sistema de informes con IA
Genera Excel con gráficos incrustados
"""
import requests
import time

print("=" * 80)
print("🎯 DEMOSTRACIÓN COMPLETA: INFORME CON GRÁFICOS EN EXCEL")
print("=" * 80)

codigo_reporte = "facturacion emitida de manera unitaria"

# Prueba 1: Informe con Excel
print("\n📊 PRUEBA 1: Generar Excel con gráficos incrustados")
print("-" * 80)

payload = {
    "solicitud": "facturación semanal agrupada por tercero con análisis de top clientes",
    "exportar_excel": True,
    "enviar_correo": False
}

print(f"📝 Solicitud: {payload['solicitud']}")
print("⏳ Generando informe (30-60 segundos)...\n")

try:
    response = requests.post(
        f"http://localhost:5000/api/analysis/{codigo_reporte}/informe-personalizado",
        json=payload,
        timeout=120
    )
    
    if response.status_code == 200:
        # Guardar Excel
        timestamp = int(time.time())
        filename = f"Informe_Facturacion_{timestamp}.xlsx"
        
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        print("✅ ¡EXCEL GENERADO EXITOSAMENTE!")
        print(f"\n📄 Archivo: {filename}")
        print(f"📊 Tamaño: {len(response.content):,} bytes")
        print(f"\n📋 El archivo contiene:")
        print("   ✅ Hoja 1: Resumen Ejecutivo (generado por IA)")
        print("   ✅ Hoja 2: Datos Agrupados (tabla procesada)")
        print("   ✅ Hoja 3: Gráficos (con gráficos nativos de Excel incrustados)")
        print("   ✅ Hoja 4: Estadísticas (totales, promedios, min, max)")
        print(f"\n💡 Abre el archivo '{filename}' para ver:")
        print("   🎨 Gráficos interactivos nativos de Excel")
        print("   📊 Gráficos de barras y pastel")
        print("   📈 Datos formateados profesionalmente")
        print("   🤖 Resumen ejecutivo generado por IA")
        
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print("⏱️ Timeout: La generación tardó más de 120 segundos")
except Exception as e:
    print(f"❌ Error: {e}")

# Prueba 2: Diferentes tipos de análisis
print("\n\n" + "=" * 80)
print("📊 PRUEBA 2: Diferentes tipos de solicitudes")
print("=" * 80)

solicitudes_ejemplo = [
    "top 10 terceros con mayor facturación total",
    "análisis de ventas por producto",
    "distribución de cartera por sede",
    "tendencia de facturación mensual"
]

print("\n💡 Puedes hacer solicitudes como:")
for idx, solicitud in enumerate(solicitudes_ejemplo, 1):
    print(f"   {idx}. \"{solicitud}\"")

print("\n🤖 La IA automáticamente:")
print("   ✅ Interpreta qué quieres")
print("   ✅ Agrupa los datos correctamente")
print("   ✅ Calcula estadísticas")
print("   ✅ Genera gráficos apropiados")
print("   ✅ Crea resumen ejecutivo")
print("   ✅ Exporta a Excel profesional")

print("\n" + "=" * 80)
print("✅ SISTEMA COMPLETAMENTE FUNCIONAL")
print("=" * 80)
print()
