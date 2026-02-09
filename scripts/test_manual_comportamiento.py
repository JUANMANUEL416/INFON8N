"""
Test manual simplificado: Gráfico en chat vs Excel
"""
import requests

BASE_URL = "http://localhost:5000"

def test_manual():
    """Test simple para verificar comportamiento"""
    
    print("\n" + "="*70)
    print("🧪 TEST MANUAL: Gráfico en Chat vs Exportar Excel")
    print("="*70)
    print("\nInstrucciones:")
    print("1. Abre http://localhost:5000/admin en tu navegador")
    print("2. Ve a la sección 'Chat con IA'")
    print("3. Selecciona un reporte (preferiblemente con datos)")
    print("="*70)
    
    # Login
    session = requests.Session()
    response = session.post(f"{BASE_URL}/login", data={
        'username': 'admin',
        'password': 'admin123'
    }, allow_redirects=False)
    
    # Obtener reportes
    response = session.get(f"{BASE_URL}/api/reportes/disponibles")
    reportes = response.json()
    
    if not reportes:
        print("\n❌ No hay reportes disponibles")
        return
    
    print(f"\n📋 Reportes disponibles:")
    for i, r in enumerate(reportes, 1):
        print(f"   {i}. {r['codigo']} - {r['nombre']}")
    
    # Seleccionar primer reporte
    codigo = reportes[0]['codigo']
    
    print(f"\n✅ Usando reporte: {codigo}")
    print("\n" + "="*70)
    print("PRUEBAS A REALIZAR:")
    print("="*70)
    
    # TEST 1: Gráfico sin Excel
    print("\n📊 TEST 1: Solicitar visualización EN EL CHAT")
    print("-"*70)
    print("Pregunta sugerida: 'muéstrame un gráfico de los top 5 terceros'")
    print("Resultado esperado:")
    print("  ✅ Respuesta en formato texto con:")
    print("     - Datos numéricos")
    print("     - Formato visual (barras █, tablas, emojis)")
    print("     - NO debe descargar Excel")
    
    pregunta1 = "muéstrame un gráfico de los top 5 terceros por valor"
    response = session.post(
        f"{BASE_URL}/api/analysis/{codigo}/pregunta",
        json={'pregunta': pregunta1}
    )
    
    content_type = response.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        print("\n✅ Respuesta: JSON (correcto)")
        data = response.json()
        respuesta = data.get('respuesta', '')
        print(f"\n{respuesta[:400]}")
    elif 'spreadsheetml.sheet' in content_type:
        print("\n❌ ERROR: Devolvió Excel (debería ser texto)")
    
    # TEST 2: Exportar a Excel
    print("\n\n📁 TEST 2: Solicitar EXPORTAR A EXCEL")
    print("-"*70)
    print("Pregunta sugerida: 'exporta a Excel los top 5 terceros'")
    print("Resultado esperado:")
    print("  ✅ Descarga automática de archivo .xlsx")
    print("  ✅ Excel con 4 hojas (Resumen, Datos, Gráficos, Estadísticas)")
    
    pregunta2 = "exporta a Excel los top 5 terceros con gráfico"
    response = session.post(
        f"{BASE_URL}/api/analysis/{codigo}/pregunta",
        json={'pregunta': pregunta2}
    )
    
    content_type = response.headers.get('content-type', '')
    
    if 'spreadsheetml.sheet' in content_type:
        print("\n✅ Archivo Excel generado (correcto)")
        print(f"   Tamaño: {len(response.content):,} bytes")
        content_disp = response.headers.get('content-disposition', '')
        if 'filename=' in content_disp:
            filename = content_disp.split('filename=')[1].strip('"')
            print(f"   Archivo: {filename}")
    elif 'application/json' in content_type:
        data = response.json()
        if 'No hay datos' in data.get('respuesta', ''):
            print("\n⚠️  Este reporte no tiene datos")
            print(f"   Mensaje: {data.get('respuesta', '')}")
        else:
            print("\n❌ ERROR: Devolvió JSON (debería ser Excel)")
            print(f"   Respuesta: {data.get('respuesta', '')[:200]}")
    
    # TEST 3: Pregunta normal
    print("\n\n💬 TEST 3: Pregunta NORMAL (sin gráfico ni Excel)")
    print("-"*70)
    print("Pregunta sugerida: '¿cuál es el total de facturación?'")
    print("Resultado esperado:")
    print("  ✅ Respuesta en formato texto")
    print("  ✅ NO debe descargar Excel")
    
    pregunta3 = "¿cuál es el total de facturación?"
    response = session.post(
        f"{BASE_URL}/api/analysis/{codigo}/pregunta",
        json={'pregunta': pregunta3}
    )
    
    content_type = response.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        print("\n✅ Respuesta: JSON (correcto)")
        data = response.json()
        print(f"   {data.get('respuesta', '')[:200]}")
    elif 'spreadsheetml.sheet' in content_type:
        print("\n❌ ERROR: Generó Excel innecesariamente")
    
    print("\n" + "="*70)
    print("✅ TESTS COMPLETADOS")
    print("="*70)
    print("\nResumen de comportamiento:")
    print("  📊 'muéstrame gráfico' → Visualización en chat (JSON)")
    print("  📁 'exporta a Excel' → Descarga archivo (.xlsx)")
    print("  💬 Preguntas normales → Respuesta texto (JSON)")
    print("\n💡 Para mejor prueba, usa el navegador en:")
    print("   http://localhost:5000/admin → Chat con IA")
    print()

if __name__ == "__main__":
    test_manual()
