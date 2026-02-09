"""
Prueba: Verificar que la IA da respuestas precisas con los datos
"""
import requests
import json

print("🧪 Probando calidad de respuestas de la IA")
print("=" * 80)

# Lista de preguntas de prueba
preguntas = [
    "¿Cuántos registros de facturación hay en total?",
    "¿Cuál es el valor total facturado?",
    "Muéstrame los 5 terceros con mayor facturación",
    "¿Puedes generar un gráfico de los principales terceros?",
    "¿Puedes exportar esto a Excel con gráficos?",
    "¿Cuál es el promedio de facturación por registro?"
]

resultados = []

for i, pregunta in enumerate(preguntas, 1):
    print(f"\n{'='*80}")
    print(f"Pregunta {i}/6: {pregunta}")
    print("-" * 80)
    
    try:
        response = requests.post(
            "http://localhost:5000/api/analysis/facturacion%20emitida%20de%20manera%20unitaria/pregunta",
            json={"pregunta": pregunta},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            respuesta = data['respuesta']
            
            print(f"\n🤖 Respuesta:\n{respuesta}\n")
            
            # Evaluar calidad
            es_buena = True
            problemas = []
            
            # Verificar frases problemáticas
            frases_malas = [
                "no tengo acceso",
                "no tengo la capacidad",
                "necesito más información",
                "no hay información",
                "no puedo proporcionar",
                "sin información explícita"
            ]
            
            for frase in frases_malas:
                if frase in respuesta.lower():
                    es_buena = False
                    problemas.append(f"Dice '{frase}'")
            
            # Verificar si responde sobre capacidades cuando se pregunta
            if "puedes" in pregunta.lower():
                if any(palabra in respuesta.lower() for palabra in ["sí", "si puedo", "puedo generar"]):
                    pass  # Correcto
                elif any(palabra in respuesta.lower() for palabra in ["no puedo", "no tengo"]):
                    es_buena = False
                    problemas.append("No reconoce sus capacidades")
            
            # Verificar que dé números cuando se piden estadísticas
            if any(palabra in pregunta.lower() for palabra in ["cuántos", "cuál es", "promedio", "total", "valor"]):
                # Buscar números en la respuesta
                import re
                numeros = re.findall(r'\d[\d,.]*\d|\d', respuesta)
                if not numeros:
                    es_buena = False
                    problemas.append("No proporciona números específicos")
            
            if es_buena:
                print("✅ RESPUESTA BUENA")
            else:
                print(f"⚠️ RESPUESTA MEJORABLE: {', '.join(problemas)}")
            
            resultados.append({
                'pregunta': pregunta,
                'buena': es_buena,
                'problemas': problemas
            })
        else:
            print(f"❌ Error HTTP {response.status_code}")
            resultados.append({
                'pregunta': pregunta,
                'buena': False,
                'problemas': [f"HTTP {response.status_code}"]
            })
    
    except Exception as e:
        print(f"❌ Error: {e}")
        resultados.append({
            'pregunta': pregunta,
            'buena': False,
            'problemas': [str(e)]
        })

# Resumen
print("\n\n" + "=" * 80)
print("📊 RESUMEN DE RESULTADOS")
print("=" * 80)

buenas = sum(1 for r in resultados if r['buena'])
total = len(resultados)

print(f"\n✅ Respuestas buenas: {buenas}/{total} ({buenas*100//total}%)")

if buenas < total:
    print(f"\n⚠️ Respuestas con problemas:")
    for r in resultados:
        if not r['buena']:
            print(f"   - {r['pregunta'][:50]}...")
            print(f"     Problemas: {', '.join(r['problemas'])}")

if buenas == total:
    print("\n🎉 PERFECTO: Todos los prompts funcionan correctamente")
elif buenas >= total * 0.8:
    print("\n✅ BIEN: La mayoría de respuestas son correctas")
else:
    print("\n⚠️ NECESITA MEJORA: Muchas respuestas tienen problemas")

print("\n💡 Si hay problemas, reiniciar backend:")
print("   docker-compose restart backend")
print()
