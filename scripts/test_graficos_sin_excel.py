"""
Test: Validar que "gráfico" muestra análisis en chat, 
y solo "exporta" genera Excel
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def login():
    """Login para obtener sesión"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/login", data={
        'username': 'admin',
        'password': 'admin123'
    }, allow_redirects=False)
    return session

def test_comportamiento_graficos():
    """Test del nuevo comportamiento de gráficos"""
    
    print("\n" + "="*60)
    print("🧪 TEST: Comportamiento Gráficos vs Excel")
    print("="*60)
    
    session = login()
    
    # Obtener primer reporte
    response = session.get(f"{BASE_URL}/api/reportes/disponibles")
    
    try:
        reportes = response.json()
    except:
        print(f"❌ Error al obtener reportes. Status: {response.status_code}")
        print(f"Respuesta: {response.text[:200]}")
        return
    
    if not reportes:
        print("❌ No hay reportes disponibles")
        return
    
    codigo = reportes[0]['codigo']
    print(f"\n📋 Usando reporte: {codigo}\n")
    
    # ========================================
    # TEST 1: Solicitar SOLO visualización
    # ========================================
    print("\n" + "-"*60)
    print("TEST 1: 'muéstrame un gráfico de los top 5' (SIN Excel)")
    print("-"*60)
    
    pregunta1 = "muéstrame un gráfico de los top 5 terceros por valor"
    
    response = session.post(
        f"{BASE_URL}/api/analysis/{codigo}/pregunta",
        json={'pregunta': pregunta1},
        allow_redirects=False
    )
    
    content_type = response.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        print("✅ CORRECTO: Respuesta JSON (texto en chat)")
        data = response.json()
        respuesta = data.get('respuesta', '')
        print(f"\n📄 Respuesta (primeros 300 chars):")
        print(respuesta[:300] + "..." if len(respuesta) > 300 else respuesta)
        
        # Validar que incluya visualización en texto
        tiene_visual = any(char in respuesta for char in ['█', '▓', '▒', '░', '|', '-'])
        tiene_numeros = any(char.isdigit() for char in respuesta)
        
        if tiene_visual:
            print("   ✅ Incluye caracteres visuales (barras, etc.)")
        if tiene_numeros:
            print("   ✅ Incluye datos numéricos")
            
    elif 'spreadsheetml.sheet' in content_type:
        print("❌ ERROR: Devolvió Excel cuando NO debería")
        print(f"   Tamaño: {len(response.content)} bytes")
    else:
        print(f"⚠️  Tipo inesperado: {content_type}")
    
    time.sleep(2)
    
    # ========================================
    # TEST 2: Solicitar Excel EXPLÍCITAMENTE
    # ========================================
    print("\n" + "-"*60)
    print("TEST 2: 'exporta esto a Excel' (CON descarga)")
    print("-"*60)
    
    pregunta2 = "exporta a Excel los top 5 terceros con gráfico de barras"
    
    response = session.post(
        f"{BASE_URL}/api/analysis/{codigo}/pregunta",
        json={'pregunta': pregunta2},
        allow_redirects=False
    )
    
    content_type = response.headers.get('content-type', '')
    
    if 'spreadsheetml.sheet' in content_type:
        print("✅ CORRECTO: Archivo Excel generado")
        print(f"   📊 Tamaño: {len(response.content):,} bytes")
        
        # Extraer filename de content-disposition
        content_disp = response.headers.get('content-disposition', '')
        if 'filename=' in content_disp:
            filename = content_disp.split('filename=')[1].strip('"')
            print(f"   📁 Archivo: {filename}")
            
    elif 'application/json' in content_type:
        print("❌ ERROR: Devolvió JSON cuando debería ser Excel")
        data = response.json()
        print(f"   Respuesta: {data.get('respuesta', '')[:200]}")
    else:
        print(f"⚠️  Tipo inesperado: {content_type}")
    
    time.sleep(2)
    
    # ========================================
    # TEST 3: Pregunta simple (control)
    # ========================================
    print("\n" + "-"*60)
    print("TEST 3: '¿cuál es el total?' (debe ser JSON)")
    print("-"*60)
    
    pregunta3 = "¿cuál es el total general de facturación?"
    
    response = session.post(
        f"{BASE_URL}/api/analysis/{codigo}/pregunta",
        json={'pregunta': pregunta3},
        allow_redirects=False
    )
    
    content_type = response.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        print("✅ CORRECTO: Respuesta JSON")
        data = response.json()
        print(f"   📄 {data.get('respuesta', '')[:150]}")
    elif 'spreadsheetml.sheet' in content_type:
        print("❌ ERROR: Generó Excel innecesariamente")
    else:
        print(f"⚠️  Tipo inesperado: {content_type}")
    
    # ========================================
    # RESUMEN
    # ========================================
    print("\n" + "="*60)
    print("✅ Tests completados")
    print("="*60)
    print("\nComportamiento esperado:")
    print("  • 'muéstrame gráfico' → Visualización en chat (JSON)")
    print("  • 'exporta a Excel' → Descarga archivo (.xlsx)")
    print("  • Preguntas normales → Respuesta texto (JSON)")
    print()

if __name__ == "__main__":
    test_comportamiento_graficos()
