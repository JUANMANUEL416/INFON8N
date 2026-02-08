"""
Script de prueba para generar informe personalizado con IA
Muestra cómo generar informes con gráficos y Excel automáticamente
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_informe_personalizado():
    """Probar generación de informe personalizado"""
    
    print("=" * 80)
    print("🤖 PRUEBA DE INFORME PERSONALIZADO CON IA")
    print("=" * 80)
    
    # 1. Obtener reportes disponibles
    print("\n1️⃣ Obteniendo reportes disponibles...")
    response = requests.get(f"{BASE_URL}/api/admin/reportes")
    
    if response.status_code != 200:
        print(f"❌ Error obteniendo reportes: {response.text}")
        return
    
    reportes = response.json()
    
    if not reportes:
        print("❌ No hay reportes disponibles")
        return
    
    print(f"✅ Se encontraron {len(reportes)} reporte(s)")
    
    for reporte in reportes:
        print(f"   - {reporte['codigo']}: {reporte['nombre']}")
    
    # Usar el primer reporte que tenga datos
    codigo_reporte = reportes[0]['codigo']
    nombre_reporte = reportes[0]['nombre']
    
    print(f"\n📊 Usando reporte: {nombre_reporte} ({codigo_reporte})")
    
    # 2. Verificar datos disponibles
    print(f"\n2️⃣ Verificando datos...")
    response = requests.get(f"{BASE_URL}/api/query/{codigo_reporte}?limite=10")
    
    if response.status_code != 200:
        print(f"❌ Error consultando datos: {response.text}")
        return
    
    datos_query = response.json()
    total_registros = datos_query.get('total', 0)
    
    print(f"✅ Hay {total_registros:,} registros disponibles")
    
    if total_registros == 0:
        print("⚠️ No hay datos para generar informe")
        return
    
    # Mostrar muestra de datos
    if datos_query.get('datos'):
        print("\n📋 Muestra de datos:")
        primer_registro = datos_query['datos'][0]['datos']
        print(f"   Campos disponibles: {', '.join(primer_registro.keys())}")
    
    # 3. Generar informe personalizado (SIN Excel ni correo primero)
    print(f"\n3️⃣ Generando informe personalizado...")
    print("   Solicitud: 'facturación semanal agrupada por tercero'")
    
    payload = {
        "solicitud": "facturación semanal agrupada por tercero",
        "exportar_excel": False,
        "enviar_correo": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/analysis/{codigo_reporte}/informe-personalizado",
        json=payload,
        timeout=60  # 60 segundos de timeout
    )
    
    if response.status_code != 200:
        print(f"❌ Error generando informe: {response.text}")
        return
    
    resultado = response.json()
    
    if not resultado.get('success'):
        print(f"❌ Error: {resultado.get('error', 'Desconocido')}")
        return
    
    informe = resultado['informe']
    
    print("\n✅ INFORME GENERADO EXITOSAMENTE!")
    print(f"\n📊 Detalles del Informe:")
    print(f"   - Reporte: {informe['reporte']}")
    print(f"   - Solicitud: {informe['solicitud']}")
    print(f"   - Total registros: {informe['total_registros']:,}")
    print(f"   - Registros procesados: {informe['registros_procesados']:,}")
    print(f"   - Fecha: {informe['fecha_generacion']}")
    
    # Agrupaciones
    if informe.get('agrupaciones'):
        print(f"\n📋 Agrupaciones:")
        agrup = informe['agrupaciones']
        print(f"   - Tipo: {agrup.get('tipo')}")
        print(f"   - Campo principal: {agrup.get('campo_principal')}")
        print(f"   - Total grupos: {agrup.get('total_grupos')}")
    
    # Estadísticas
    if informe.get('estadisticas'):
        print(f"\n📈 Estadísticas:")
        stats = informe['estadisticas']
        if stats.get('total'):
            print(f"   Totales:")
            for campo, valor in stats['total'].items():
                print(f"      - {campo}: {valor:,.2f}")
        if stats.get('promedio'):
            print(f"   Promedios:")
            for campo, valor in stats['promedio'].items():
                print(f"      - {campo}: {valor:,.2f}")
    
    # Gráficos
    if informe.get('graficos'):
        print(f"\n📊 Gráficos generados: {len(informe['graficos'])}")
        for idx, grafico in enumerate(informe['graficos'], 1):
            print(f"   {idx}. {grafico['titulo']} ({grafico['tipo']})")
            print(f"      - Elementos: {len(grafico['labels'])}")
    
    # Resumen ejecutivo
    if informe.get('resumen_ejecutivo'):
        print(f"\n📝 RESUMEN EJECUTIVO:")
        print("   " + "=" * 76)
        # Mostrar primeras 10 líneas
        lineas = informe['resumen_ejecutivo'].split('\n')[:10]
        for linea in lineas:
            print(f"   {linea}")
        if len(informe['resumen_ejecutivo'].split('\n')) > 10:
            print("   ...")
        print("   " + "=" * 76)
    
    # Datos procesados (muestra)
    if informe.get('datos_procesados'):
        print(f"\n📋 Datos Procesados (Top 10):")
        for idx, registro in enumerate(informe['datos_procesados'][:10], 1):
            print(f"   {idx}. {registro}")
    
    # 4. Ahora probar con exportación a Excel
    print(f"\n4️⃣ Ahora generando con exportación a Excel...")
    
    payload_excel = {
        "solicitud": "top 10 terceros con mayor facturación total",
        "exportar_excel": True,
        "enviar_correo": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/analysis/{codigo_reporte}/informe-personalizado",
        json=payload_excel,
        timeout=60
    )
    
    if response.status_code == 200:
        # El endpoint retorna el archivo Excel directamente
        filename = f"informe_prueba_{int(time.time())}.xlsx"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"✅ Excel generado correctamente: {filename}")
        print(f"   Tamaño: {len(response.content):,} bytes")
    else:
        print(f"⚠️ No se pudo generar Excel: {response.status_code}")
    
    # 5. Opcional: Probar envío por correo (solo si está configurado)
    print(f"\n5️⃣ Prueba de envío por correo (opcional)...")
    print("   ⚠️ Esto requiere configurar MAIL_USERNAME y MAIL_PASSWORD en .env")
    
    test_email = input("\n   ¿Deseas probar el envío por correo? Ingresa tu email o presiona Enter para omitir: ").strip()
    
    if test_email and '@' in test_email:
        print(f"   Enviando informe a {test_email}...")
        
        payload_correo = {
            "solicitud": "resumen ejecutivo de facturación por tercero",
            "exportar_excel": True,
            "enviar_correo": True,
            "destinatarios": [test_email]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/analysis/{codigo_reporte}/informe-personalizado",
            json=payload_correo,
            timeout=60
        )
        
        if response.status_code == 200:
            resultado_correo = response.json()
            if resultado_correo.get('correo_enviado'):
                print(f"   ✅ Correo enviado exitosamente a {test_email}")
                print(f"   📧 Revisa tu bandeja de entrada")
            else:
                print(f"   ℹ️ Informe generado pero no se envió correo")
        else:
            print(f"   ❌ Error: {response.text}")
    else:
        print("   ⏭️ Omitiendo prueba de correo")
    
    print("\n" + "=" * 80)
    print("✅ PRUEBA COMPLETADA")
    print("=" * 80)
    print("\n💡 Ejemplos de solicitudes que puedes hacer:")
    print("   - 'facturación mensual agrupada por cliente'")
    print("   - 'top 20 terceros con mayor facturación'")
    print("   - 'análisis de gastos por categoría'")
    print("   - 'ventas diarias por producto'")
    print("   - 'distribución de cartera por sede'")
    print("\n🔧 La IA interpretará tu solicitud y generará:")
    print("   ✅ Agrupaciones automáticas")
    print("   ✅ Gráficos relevantes (barras, pastel, líneas)")
    print("   ✅ Excel con múltiples hojas y gráficos incrustados")
    print("   ✅ Resumen ejecutivo con insights de IA")
    print("   ✅ Opción de envío por correo con adjuntos")

if __name__ == "__main__":
    try:
        test_informe_personalizado()
    except KeyboardInterrupt:
        print("\n\n⚠️ Prueba cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
