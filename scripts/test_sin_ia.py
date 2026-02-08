"""
Prueba del informe personalizado en modo básico (sin necesitar OpenAI)
"""
import requests

print("=" * 70)
print("🤖 PRUEBA DE INFORME PERSONALIZADO")
print("=" * 70)
print("\n📊 Generando informe básico (sin IA)...\n")

codigo_reporte = "facturacion emitida de manera unitaria"

# Solicitud simple
payload = {
    "solicitud": "agrupacion por tercero",  # Detectará automáticamente
    "exportar_excel": True,  # Generar Excel
    "enviar_correo": False
}

try:
    response = requests.post(
        f"http://localhost:5000/api/analysis/{codigo_reporte}/informe-personalizado",
        json=payload,
        timeout=90
    )
    
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        # Si exportar_excel=True, retorna el archivo
        if response.headers.get('content-type') == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            filename = "informe_facturacion.xlsx"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print("✅ ¡EXCEL GENERADO EXITOSAMENTE!")
            print(f"📄 Archivo: {filename}")
            print(f"📊 Tamaño: {len(response.content):,} bytes")
            print(f"\n💡 Abre el archivo {filename} para ver:")
            print("   - Hoja 1: Resumen Ejecutivo")
            print("   - Hoja 2: Datos Agrupados")
            print("   - Hoja 3: Gráficos (con gráficos nativos de Excel)")
            print("   - Hoja 4: Estadísticas")
            print("\n🎨 Los gráficos son nativos de Excel e interactivos!")
        else:
            # Retornó JSON
            resultado = response.json()
            if resultado.get('success'):
                print("✅ Informe generado!")
                print(f"📊 Datos procesados: {len(resultado['informe']['datos_procesados'])}")
    else:
        error_data = response.json()
        print(f"❌ Error: {error_data.get('error')}")
        
        if "OpenAI" in error_data.get('error', ''):
            print("\n💡 SOLUCIÓN:")
            print("   1. Obtén una API key en: https://platform.openai.com/api-keys")
            print("   2. Crea archivo .env con: OPENAI_API_KEY=sk-tu-key")
            print("   3. Reinicia: docker-compose restart backend")
            print("\n   O bien, el sistema puede trabajar en modo básico sin IA")
            print("   (sin resumen ejecutivo generado por IA)")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
