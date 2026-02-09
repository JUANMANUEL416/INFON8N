"""
Script de prueba para verificar mejoras en chat IA
- IA responde sin mostrar código
- Excel se descarga automáticamente
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

def probar_chat_mejorado():
    print("=" * 80)
    print("🧪 PRUEBA DE MEJORAS EN CHAT IA")
    print("=" * 80)
    
    # Usar el reporte existente de facturación
    codigo_reporte = 'facturacion emitida de manera unitaria'
    
    # Preguntas de prueba
    pruebas = [
        {
            'pregunta': 'Muéstrame el top 5 de terceros por valor total',
            'tipo': 'texto',
            'espera': 'Respuesta con datos concretos, SIN mencionar código'
        },
        {
            'pregunta': 'Genera un gráfico de barras de la distribución por estado',
            'tipo': 'excel',
            'espera': 'Descarga automática de Excel con gráficos'
        },
        {
            'pregunta': 'Exporta a Excel el análisis de facturación por tercero',
            'tipo': 'excel',
            'espera': 'Descarga automática de Excel'
        }
    ]
    
    for i, prueba in enumerate(pruebas, 1):
        print(f"\n{'='*80}")
        print(f"Prueba {i}/{len(pruebas)}: {prueba['pregunta']}")
        print(f"Tipo esperado: {prueba['tipo']}")
        print('-' * 80)
        
        try:
            response = requests.post(
                f'{BASE_URL}/api/analysis/{requests.utils.quote(codigo_reporte)}/pregunta',
                json={'pregunta': prueba['pregunta']},
                timeout=30
            )
            
            content_type = response.headers.get('content-type', '')
            
            if 'spreadsheetml.sheet' in content_type:
                # Es un archivo Excel
                print("✅ RESPUESTA: Archivo Excel")
                
                filename = 'descarga_prueba.xlsx'
                content_disposition = response.headers.get('content-disposition', '')
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')
                
                print(f"   📄 Nombre del archivo: {filename}")
                print(f"   📊 Tamaño: {len(response.content) / 1024:.2f} KB")
                print(f"   ✅ El archivo se descargaría automáticamente en el navegador")
                
                if prueba['tipo'] != 'excel':
                    print(f"   ⚠️  ADVERTENCIA: Se esperaba '{prueba['tipo']}' pero recibió Excel")
                else:
                    print(f"   ✅ Tipo correcto: {prueba['tipo']}")
                
            elif 'application/json' in content_type:
                # Es respuesta JSON
                data = response.json()
                print("✅ RESPUESTA: JSON")
                
                if 'respuesta' in data:
                    respuesta = data['respuesta']
                    print(f"\n   🤖 Respuesta de IA:")
                    print(f"   {'-'*76}")
                    
                    # Verificar que NO contenga palabras prohibidas
                    palabras_prohibidas = [
                        'he generado',
                        'puedes descargar',
                        'archivo excel',
                        'matplotlib',
                        'pandas',
                        'python',
                        'import',
                        'def ',
                        'plt.',
                        'se ha generado',
                        'se está generando'
                    ]
                    
                    respuesta_lower = respuesta.lower()
                    encontradas = [p for p in palabras_prohibidas if p in respuesta_lower]
                    
                    # Mostrar primeras 300 caracteres
                    if len(respuesta) > 300:
                        print(f"   {respuesta[:300]}...")
                    else:
                        print(f"   {respuesta}")
                    
                    print(f"   {'-'*76}")
                    
                    if encontradas:
                        print(f"\n   ❌ PROBLEMA: La IA mencionó procesos técnicos:")
                        for palabra in encontradas:
                            print(f"      - '{palabra}'")
                    else:
                        print(f"\n   ✅ IA responde solo con RESULTADOS (sin código ni procesos)")
                    
                    if prueba['tipo'] == 'excel':
                        print(f"   ⚠️  Se esperaba Excel pero recibió JSON")
                
                if 'grafico' in data:
                    print(f"\n   📊 Incluye gráfico embebido en base64")
                
                if prueba['tipo'] != 'texto':
                    print(f"   ⚠️  ADVERTENCIA: Se esperaba '{prueba['tipo']}' pero recibió JSON")
                
            else:
                print(f"❌ Tipo de contenido inesperado: {content_type}")
            
            print(f"\n   Status Code: {response.status_code}")
            
        except requests.exceptions.Timeout:
            print("❌ ERROR: Timeout (la IA tardó más de 30 segundos)")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n{'='*80}")
    print("🎯 RESUMEN DE PRUEBAS")
    print('='*80)
    print("\n✅ Mejoras implementadas:")
    print("   1. IA responde solo con RESULTADOS (no describe procesos)")
    print("   2. Detección automática de solicitudes de gráficos/Excel")
    print("   3. Descarga automática de Excel cuando se solicitan gráficos")
    print("   4. Frontend maneja archivos Excel correctamente")
    print("\n💡 Para probar visualmente:")
    print("   1. Abre http://localhost:5000/admin")
    print("   2. Ve a 'Análisis IA' → Tab 'Chat con IA'")
    print("   3. Pregunta: 'Muéstrame un gráfico de barras por estado'")
    print("   4. El Excel se descargará automáticamente")
    print("   5. La respuesta NO mostrará código ni proceso")

if __name__ == '__main__':
    try:
        probar_chat_mejorado()
    except Exception as e:
        print(f"\n❌ Error general: {e}")
        import traceback
        traceback.print_exc()
