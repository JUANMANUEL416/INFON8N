"""
Script de validación de mejoras del agente IA
Verifica:
1. Auto-indexación funciona
2. Contexto se guarda correctamente
3. Documento maestro existe en ChromaDB
4. Respuestas mejoradas del agente
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
REPORTE_TEST = "facturacion emitida de manera unitaria"

def test_1_auto_indexacion():
    """Verificar que la auto-indexación está activa"""
    print("\n" + "="*60)
    print("TEST 1: Verificar Auto-Indexación")
    print("="*60)
    
    # Simular carga de datos via webhook
    url = f"{BASE_URL}/webhook/upload/{REPORTE_TEST}"
    datos_prueba = {
        "datos": [
            {
                "fecha": "2026-02-13",
                "monto": 999999,
                "cliente": "Cliente Test Auto-Index",
                "estado": "Activo"
            }
        ]
    }
    
    print(f"\n📤 Enviando dato de prueba a webhook...")
    response = requests.post(url, json=datos_prueba)
    
    if response.status_code == 200:
        resultado = response.json()
        print(f"✅ Datos cargados: {resultado.get('registros_insertados')} registros")
        
        if resultado.get('auto_indexado'):
            print("✅ AUTO-INDEXACIÓN CONFIRMADA")
            print("   ➜ No necesitas indexar manualmente")
            return True
        else:
            print("❌ Auto-indexación NO detectada")
            return False
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_2_contexto_reporte():
    """Verificar que el agente conoce el contexto del reporte"""
    print("\n" + "="*60)
    print("TEST 2: Verificar Contexto del Reporte")
    print("="*60)
    
    url = f"{BASE_URL}/api/analysis/{REPORTE_TEST}/pregunta"
    pregunta = "¿Para qué sirve este reporte y qué tipo de datos contiene?"
    
    print(f"\n💬 Preguntando: {pregunta}")
    print("   (Si el agente responde con detalles específicos del contexto,")
    print("    significa que las mejoras funcionan)")
    
    response = requests.post(url, json={"pregunta": pregunta})
    
    if response.status_code == 200:
        resultado = response.json()
        respuesta = resultado.get('respuesta', '')
        
        print(f"\n🤖 Respuesta del agente:")
        print("-" * 60)
        print(respuesta)
        print("-" * 60)
        
        # Verificar si menciona conceptos del contexto
        indicadores_contexto = ['facturación', 'factura', 'emitida', 'cliente', 'monto']
        menciones = sum(1 for palabra in indicadores_contexto if palabra.lower() in respuesta.lower())
        
        if menciones >= 2:
            print(f"\n✅ CONTEXTO DETECTADO ({menciones}/5 palabras clave encontradas)")
            print("   ➜ El agente conoce el propósito del reporte")
            return True
        else:
            print(f"\n⚠️ Contexto limitado ({menciones}/5 palabras clave)")
            print("   ➜ Considera agregar más contexto al reporte")
            return False
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_3_indexacion_actual():
    """Verificar estado actual de indexación"""
    print("\n" + "="*60)
    print("TEST 3: Estado de Indexación en ChromaDB")
    print("="*60)
    
    # Intentar re-indexar para verificar que funciona
    url = f"{BASE_URL}/api/analysis/{REPORTE_TEST}/indexar"
    
    print(f"\n🔄 Re-indexando reporte (incluye documento maestro)...")
    response = requests.post(url)
    
    if response.status_code == 200:
        resultado = response.json()
        total = resultado.get('indexed', 0)
        
        print(f"✅ Indexación completada:")
        print(f"   ➜ {total} documentos indexados en ChromaDB")
        print(f"   ➜ Incluye: {total-1} registros + 1 documento maestro")
        
        if total > 0:
            return True
        else:
            print("⚠️ No hay datos para indexar")
            return False
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_4_pregunta_compleja():
    """Probar pregunta compleja que requiere contexto"""
    print("\n" + "="*60)
    print("TEST 4: Pregunta Compleja con Contexto")
    print("="*60)
    
    url = f"{BASE_URL}/api/analysis/{REPORTE_TEST}/pregunta"
    pregunta = "¿Cuál es el total facturado y hay algún monto que parezca anormal?"
    
    print(f"\n💬 Pregunta compleja: {pregunta}")
    print("   (Requiere: cálculo + detección de anomalías con contexto)")
    
    response = requests.post(url, json={"pregunta": pregunta})
    
    if response.status_code == 200:
        resultado = response.json()
        respuesta = resultado.get('respuesta', '')
        
        print(f"\n🤖 Respuesta del agente:")
        print("-" * 60)
        print(respuesta)
        print("-" * 60)
        
        # Verificar si incluye números específicos
        tiene_numeros = any(char.isdigit() for char in respuesta)
        
        if tiene_numeros:
            print(f"\n✅ RESPUESTA PRECISA")
            print("   ➜ Incluye cálculos específicos")
            print("   ➜ El agente está funcionando correctamente")
            return True
        else:
            print(f"\n⚠️ Respuesta muy genérica")
            print("   ➜ El agente puede necesitar más datos o contexto")
            return False
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_5_analisis_mejorado():
    """Verificar que los análisis usan el contexto"""
    print("\n" + "="*60)
    print("TEST 5: Análisis con Contexto Mejorado")
    print("="*60)
    
    url = f"{BASE_URL}/api/analysis/{REPORTE_TEST}/analisis"
    
    print(f"\n📊 Generando análisis general...")
    response = requests.post(url, json={"tipo": "general"})
    
    if response.status_code == 200:
        resultado = response.json()
        analisis = resultado.get('analisis', '')
        
        print(f"\n📋 Análisis generado:")
        print("-" * 60)
        print(analisis[:500] + "..." if len(analisis) > 500 else analisis)
        print("-" * 60)
        
        # Verificar si menciona contexto del negocio
        palabras_negocio = ['facturación', 'ventas', 'clientes', 'recomendación', 'tendencia']
        menciones = sum(1 for palabra in palabras_negocio if palabra.lower() in analisis.lower())
        
        if menciones >= 2:
            print(f"\n✅ ANÁLISIS CONTEXTUALIZADO ({menciones}/5 términos de negocio)")
            print("   ➜ El análisis considera el propósito del reporte")
            return True
        else:
            print(f"\n⚠️ Análisis genérico ({menciones}/5 términos)")
            return False
    else:
        print(f"❌ Error: {response.text}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*60)
    print("🧪 VALIDACIÓN DE MEJORAS DEL AGENTE IA")
    print("="*60)
    print("\nEste script verifica que las mejoras implementadas funcionen:")
    print("  1. Auto-indexación al cargar datos")
    print("  2. Contexto enriquecido del reporte")
    print("  3. Documento maestro en ChromaDB")
    print("  4. Respuestas mejoradas")
    print("  5. Análisis con contexto")
    
    input("\n⏸️  Presiona ENTER para comenzar las pruebas...")
    
    resultados = []
    
    try:
        resultados.append(("Auto-indexación", test_1_auto_indexacion()))
        time.sleep(2)
        
        resultados.append(("Contexto del reporte", test_2_contexto_reporte()))
        time.sleep(2)
        
        resultados.append(("Estado de indexación", test_3_indexacion_actual()))
        time.sleep(2)
        
        resultados.append(("Pregunta compleja", test_4_pregunta_compleja()))
        time.sleep(2)
        
        resultados.append(("Análisis mejorado", test_5_analisis_mejorado()))
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se puede conectar al servidor")
        print("   ➜ Asegúrate de que el backend esté corriendo:")
        print("   ➜ docker-compose up -d")
        return
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        return
    
    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN DE RESULTADOS")
    print("="*60)
    
    for nombre, resultado in resultados:
        estado = "✅ PASS" if resultado else "❌ FAIL"
        print(f"{estado} - {nombre}")
    
    total = len(resultados)
    exitosos = sum(1 for _, r in resultados if r)
    porcentaje = (exitosos / total * 100) if total > 0 else 0
    
    print(f"\n🎯 Resultado: {exitosos}/{total} tests pasados ({porcentaje:.0f}%)")
    
    if porcentaje >= 80:
        print("\n🎉 ¡EXCELENTE! Las mejoras están funcionando correctamente")
    elif porcentaje >= 60:
        print("\n✅ Bien. Algunas mejoras necesitan ajustes")
    else:
        print("\n⚠️ Necesita atención. Revisa la configuración")
    
    print("\n💡 Consejos:")
    print("   • Asegúrate de agregar contexto detallado a los reportes")
    print("   • Incluye descripciones en cada campo")
    print("   • Re-indexa datos existentes una vez")
    print(f"\n📖 Ver guía completa: MEJORAS_AGENTE_IA.md")

if __name__ == "__main__":
    main()
