"""
Test de Memoria Conversacional + Function Calling
Demuestra las nuevas capacidades del agente IA
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"
REPORTE = "facturacion emitida de manera unitaria"
SESSION_ID = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def print_separador(titulo=""):
    print("\n" + "="*70)
    if titulo:
        print(f"  {titulo}")
        print("="*70)

def print_respuesta(respuesta_json):
    """Formatear y mostrar respuesta del agente"""
    print(f"\n🤖 Respuesta del agente:")
    print("-" * 70)
    print(respuesta_json.get('respuesta', 'Sin respuesta'))
    print("-" * 70)
    
    if respuesta_json.get('funciones_ejecutadas'):
        print(f"\n🔧 Funciones ejecutadas: {', '.join(respuesta_json['funciones_ejecutadas'])}")
    
    print(f"📊 Session ID: {respuesta_json.get('session_id', 'N/A')}")
    return respuesta_json

def hacer_pregunta(pregunta, session_id=SESSION_ID):
    """Hacer una pregunta al agente"""
    url = f"{BASE_URL}/api/analysis/{REPORTE}/pregunta"
    
    print(f"\n💬 Usuario: {pregunta}")
    
    response = requests.post(url, json={
        "pregunta": pregunta,
        "session_id": session_id
    })
    
    if response.status_code == 200:
        return print_respuesta(response.json())
    else:
        print(f"❌ Error: {response.text}")
        return None

def obtener_historial(session_id=SESSION_ID):
    """Obtener historial de conversación"""
    url = f"{BASE_URL}/api/analysis/{REPORTE}/session/{session_id}/historial"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📚 Historial de conversación (Session: {session_id})")
        print(f"   Total de {data['mensajes']} mensajes")
        
        for i, msg in enumerate(data['historial'], 1):
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            print(f"   {i}. {role_emoji} {msg['role']}: {msg['content'][:60]}...")
        
        return data
    else:
        print(f"❌ Error obteniendo historial: {response.text}")
        return None

def limpiar_sesion(session_id=SESSION_ID):
    """Limpiar historial de una sesión"""
    url = f"{BASE_URL}/api/analysis/{REPORTE}/session/{session_id}/limpiar"
    
    response = requests.post(url)
    
    if response.status_code == 200:
        print(f"\n🧹 Sesión {session_id} limpiada")
        return True
    else:
        print(f"❌ Error limpiando sesión: {response.text}")
        return False

def demo_function_calling():
    """Demo de Function Calling - El agente ejecuta funciones automáticamente"""
    
    print_separador("🔧 DEMO 1: FUNCTION CALLING")
    print("\nEl agente EJECUTA FUNCIONES automáticamente para obtener datos precisos")
    
    # Test 1: Calcular totales
    hacer_pregunta("¿Cuál es el total facturado?")
    time.sleep(2)
    
    # Test 2: Agrupar datos (Top N)
    hacer_pregunta("Dame el top 5 de clientes con mayor facturación")
    time.sleep(2)
    
    # Test 3: Contar registros
    hacer_pregunta("¿Cuántas facturas hay en estado Activo?")
    time.sleep(2)

def demo_memoria_conversacional():
    """Demo de Memoria Conversacional - El agente recuerda el contexto"""
    
    print_separador("🧠 DEMO 2: MEMORIA CONVERSACIONAL")
    print("\nEl agente RECUERDA el contexto de la conversación anterior")
    
    # Primera pregunta - establece contexto
    hacer_pregunta("¿Cuál es el total facturado este mes?")
    time.sleep(2)
    
    # Segunda pregunta - usa contexto previo (no especifica "facturado")
    hacer_pregunta("¿Y el mes pasado?")
    time.sleep(2)
    
    # Tercera pregunta - continúa el contexto
    hacer_pregunta("¿Cuál fue la diferencia?")
    time.sleep(2)
    
    # Mostrar historial
    obtener_historial()

def demo_comparaciones():
    """Demo de Comparaciones entre períodos"""
    
    print_separador("📊 DEMO 3: COMPARACIONES AUTOMÁTICAS")
    print("\nEl agente puede comparar períodos automáticamente")
    
    # Comparación temporal
    hacer_pregunta("Compara la facturación de enero vs febrero 2026")
    time.sleep(2)

def demo_estadisticas():
    """Demo de Estadísticas detalladas"""
    
    print_separador("📈 DEMO 4: ESTADÍSTICAS DETALLADAS")
    print("\nEl agente puede obtener estadísticas completas de cualquier campo")
    
    hacer_pregunta("Dame estadísticas detalladas del campo monto")
    time.sleep(2)

def demo_conversacion_natural():
    """Demo de Conversación Natural completa"""
    
    print_separador("💬 DEMO 5: CONVERSACIÓN NATURAL COMPLETA")
    print("\nConversación fluida con contexto y funciones automáticas")
    
    # Nueva sesión para esta demo
    nueva_session = f"demo_natural_{datetime.now().strftime('%H%M%S')}"
    
    hacer_pregunta("Hola, ¿qué datos tienes disponibles?", nueva_session)
    time.sleep(2)
    
    hacer_pregunta("Muéstrame el total", nueva_session)
    time.sleep(2)
    
    hacer_pregunta("¿Es bueno ese monto?", nueva_session)
    time.sleep(2)
    
    hacer_pregunta("¿Quiénes son los principales clientes?", nueva_session)
    time.sleep(2)
    
    # Mostrar historial de esta sesión
    obtener_historial(nueva_session)

def main():
    """Ejecutar todas las demos"""
    
    print("\n" + "="*70)
    print("  🚀 DEMOSTRACIÓN: MEMORIA + FUNCTION CALLING")
    print("="*70)
    print("\nEsta demo muestra las nuevas capacidades del agente IA:")
    print("  ✅ Memoria conversacional - Recuerda el contexto")
    print("  ✅ Function calling - Ejecuta funciones automáticamente")
    print("  ✅ Cálculos precisos - Totales, promedios, rankings")
    print("  ✅ Comparaciones temporales - Entre períodos")
    print("  ✅ Estadísticas detalladas - Análisis completos")
    
    input("\n⏸️  Presiona ENTER para comenzar...")
    
    try:
        # Demo 1: Function Calling
        demo_function_calling()
        input("\n⏸️  Presiona ENTER para continuar con Demo 2...")
        
        # Demo 2: Memoria Conversacional
        demo_memoria_conversacional()
        input("\n⏸️  Presiona ENTER para continuar con Demo 3...")
        
        # Demo 3: Comparaciones
        demo_comparaciones()
        input("\n⏸️  Presiona ENTER para continuar con Demo 4...")
        
        # Demo 4: Estadísticas
        demo_estadisticas()
        input("\n⏸️  Presiona ENTER para continuar con Demo 5...")
        
        # Demo 5: Conversación Natural
        demo_conversacion_natural()
        
        # Resumen final
        print_separador("📊 RESUMEN FINAL")
        print("\n✅ Todas las demos completadas con éxito!")
        print("\n💡 Lo que acabas de ver:")
        print("  • El agente EJECUTA funciones automáticamente")
        print("  • RECUERDA el contexto de conversaciones previas")
        print("  • Da respuestas PRECISAS con datos reales")
        print("  • Entiende preguntas en lenguaje NATURAL")
        print("\n🎯 El agente ahora es MUCHO más inteligente y útil!")
        
        print("\n📖 Documentación completa en: MEJORAS_FUNCTION_CALLING.md")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se puede conectar al servidor")
        print("   ➜ Asegúrate de que el backend esté corriendo:")
        print("   ➜ docker-compose up -d")
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")

if __name__ == "__main__":
    main()
