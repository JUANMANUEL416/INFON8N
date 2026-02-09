"""
Agente de análisis de datos con IA
Utiliza ChromaDB para embeddings y OpenAI para análisis
"""
import os
import json
import logging
from typing import List, Dict, Optional
import chromadb
from openai import OpenAI
import pandas as pd
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Backend sin interfaz gráfica
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

# Configurar estilo de gráficos
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

class DataAnalysisAgent:
    """Agente para análisis y consulta de datos con IA"""
    
    def __init__(self, db_manager, openai_api_key: Optional[str] = None):
        self.db_manager = db_manager
        self._chroma_client = None
        self._openai_client = None
        
        # Guardar API key para lazy loading
        self.openai_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.openai_key:
            logger.warning("No se configuró OPENAI_API_KEY. Algunas funciones estarán limitadas.")
    
    @property
    def openai_client(self):
        """Lazy loading de OpenAI client"""
        if self._openai_client is None and self.openai_key:
            try:
                self._openai_client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                logger.error(f"Error inicializando OpenAI: {e}")
                raise Exception("No se pudo inicializar OpenAI. Verifica tu API key.")
        return self._openai_client
    
    @property
    def chroma_client(self):
        """Lazy loading de ChromaDB client"""
        if self._chroma_client is None:
            try:
                self._chroma_client = chromadb.HttpClient(host='chroma', port=8000)
            except Exception as e:
                logger.error(f"Error conectando a ChromaDB: {e}")
                raise Exception("ChromaDB no disponible. Asegúrate de que el servicio esté corriendo.")
        return self._chroma_client
    
    def indexar_datos_reporte(self, codigo_reporte: str):
        """Indexar datos de un reporte en ChromaDB para búsqueda semántica"""
        try:
            # Obtener configuración del reporte
            reporte = self.db_manager.obtener_reporte(codigo_reporte)
            if not reporte:
                raise ValueError(f"Reporte {codigo_reporte} no encontrado")
            
            # Obtener datos
            datos = self.db_manager.consultar_datos(codigo_reporte, limite=1000)
            
            if not datos:
                logger.info(f"No hay datos para indexar en {codigo_reporte}")
                return {'indexed': 0}
            
            # Crear o obtener colección
            collection_name = f"reporte_{codigo_reporte.replace(' ', '_')}"
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"reporte": codigo_reporte}
            )
            
            # Preparar documentos para indexar
            documents = []
            metadatas = []
            ids = []
            
            for idx, registro in enumerate(datos):
                # Convertir datos a texto descriptivo
                datos_dict = registro['datos']
                texto = f"Registro del reporte {reporte['nombre']}:\n"
                texto += "\n".join([f"{k}: {v}" for k, v in datos_dict.items() if v is not None])
                
                documents.append(texto)
                metadatas.append({
                    'id_registro': str(registro['id']),
                    'fecha_carga': str(registro['created_at']),
                    'reporte': codigo_reporte
                })
                ids.append(f"{codigo_reporte}_{registro['id']}")
            
            # Indexar en lotes
            batch_size = 100
            total_indexed = 0
            
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
                total_indexed += len(batch_docs)
            
            logger.info(f"Indexados {total_indexed} registros de {codigo_reporte}")
            
            return {
                'indexed': total_indexed,
                'collection': collection_name
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error indexando datos: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def consultar_con_lenguaje_natural(self, codigo_reporte: str, pregunta: str, limite: int = 5):
        """Buscar datos usando lenguaje natural"""
        try:
            collection_name = f"reporte_{codigo_reporte.replace(' ', '_')}"
            
            try:
                collection = self.chroma_client.get_or_create_collection(
                    name=collection_name,
                    metadata={"reporte": codigo_reporte}
                )
                # Si la colección existe pero está vacía, indexar
                if collection.count() == 0:
                    self.indexar_datos_reporte(codigo_reporte)
                    collection = self.chroma_client.get_collection(collection_name)
            except Exception as e:
                logger.error(f"Error al obtener/crear colección: {e}")
                # Si no existe, indexar primero
                self.indexar_datos_reporte(codigo_reporte)
                collection = self.chroma_client.get_collection(collection_name)
            
            # Buscar en ChromaDB
            resultados = collection.query(
                query_texts=[pregunta],
                n_results=limite
            )
            
            return {
                'pregunta': pregunta,
                'resultados': resultados['documents'][0] if resultados['documents'] else [],
                'metadatos': resultados['metadatas'][0] if resultados['metadatas'] else []
            }
            
        except Exception as e:
            logger.error(f"Error en consulta: {e}")
            raise
    
    def generar_analisis_ia(self, codigo_reporte: str, tipo_analisis: str = 'general'):
        """Generar análisis con IA de los datos"""
        if not self.openai_client:
            return {'error': 'OpenAI no configurado'}
        
        try:
            # Obtener muestra de datos
            reporte = self.db_manager.obtener_reporte(codigo_reporte)
            datos = self.db_manager.consultar_datos(codigo_reporte, limite=100)
            
            if not datos:
                return {'error': 'No hay datos para analizar'}
            
            # Convertir a DataFrame para estadísticas
            df_datos = pd.DataFrame([d['datos'] for d in datos])
            
            # Generar resumen estadístico
            resumen = {
                'total_registros': len(datos),
                'columnas': list(df_datos.columns),
                'muestra_datos': df_datos.head(5).to_dict('records')
            }
            
            # Estadísticas numéricas
            numericas = df_datos.select_dtypes(include=['number']).describe().to_dict()
            
            # Generar datos para gráficos
            graficos = self._generar_datos_graficos(df_datos)
            
            # Prompt para el análisis
            if tipo_analisis == 'general':
                prompt = f"""Analiza los siguientes datos del reporte "{reporte['nombre']}":

Total de registros: {resumen['total_registros']}
Columnas: {', '.join(resumen['columnas'])}

Estadísticas numéricas:
{json.dumps(numericas, indent=2)}

Muestra de datos:
{json.dumps(resumen['muestra_datos'], indent=2)}

Proporciona un análisis detallado que incluya:
1. Resumen ejecutivo
2. Insights principales
3. Tendencias identificadas
4. Recomendaciones
5. Alertas o anomalías (si las hay)

Responde en español y de forma clara y profesional."""

            elif tipo_analisis == 'tendencias':
                prompt = f"""Analiza las tendencias en los datos del reporte "{reporte['nombre']}".
                
Datos disponibles: {resumen['total_registros']} registros
Columnas: {', '.join(resumen['columnas'])}

Identifica:
1. Tendencias temporales
2. Patrones recurrentes  
3. Proyecciones futuras
4. Cambios significativos

Datos de muestra:
{json.dumps(resumen['muestra_datos'], indent=2)}"""

            elif tipo_analisis == 'anomalias':
                prompt = f"""Detecta anomalías en los datos del reporte "{reporte['nombre']}".

Estadísticas:
{json.dumps(numericas, indent=2)}

Identifica valores atípicos, inconsistencias o datos sospechosos.
Muestra: {json.dumps(resumen['muestra_datos'], indent=2)}"""
            
            # Llamar a OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """Eres un analista de datos experto con capacidades avanzadas de visualización.
                    
Capacidades del sistema:
                    - Generas gráficos profesionales (barras, torta, líneas) automáticamente
                    - Exportas informes a Excel con gráficos nativos incrustados
                    - Creas visualizaciones con matplotlib, seaborn y xlsxwriter
                    - Envías informes por correo electrónico con adjuntos
                    
                    Cuando te soliciten gráficos, reportes Excel o visualizaciones, SIEMPRE confirma que puedes hacerlo.
                    Proporciona insights valiosos y recomendaciones basadas en datos."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            analisis = response.choices[0].message.content
            
            return {
                'tipo_analisis': tipo_analisis,
                'reporte': reporte['nombre'],
                'total_registros': resumen['total_registros'],
                'analisis': analisis,
                'graficos': graficos,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando análisis: {e}")
            raise
    
    def _generar_datos_graficos(self, df: pd.DataFrame):
        """Generar datos estructurados para gráficos"""
        graficos = []
        
        try:
            # Gráfico de barras para columnas numéricas principales
            columnas_numericas = df.select_dtypes(include=['number']).columns[:5]
            for col in columnas_numericas:
                if df[col].notna().sum() > 0:
                    # Top 10 valores
                    top_values = df[col].value_counts().head(10)
                    if len(top_values) > 0:
                        graficos.append({
                            'tipo': 'bar',
                            'titulo': f'Top 10 - {col}',
                            'labels': [str(x) for x in top_values.index.tolist()],
                            'datos': top_values.values.tolist(),
                            'columna': col
                        })
            
            # Gráfico de torta para columnas categóricas
            columnas_texto = df.select_dtypes(include=['object']).columns[:3]
            for col in columnas_texto:
                if df[col].notna().sum() > 0:
                    value_counts = df[col].value_counts().head(8)
                    if len(value_counts) > 1:
                        graficos.append({
                            'tipo': 'pie',
                            'titulo': f'Distribución - {col}',
                            'labels': [str(x) for x in value_counts.index.tolist()],
                            'datos': value_counts.values.tolist(),
                            'columna': col
                        })
            
            # Estadísticas resumidas para gráfico de resumen
            if len(columnas_numericas) > 0:
                stats = df[columnas_numericas].sum().head(5)
                if len(stats) > 0:
                    graficos.append({
                        'tipo': 'bar',
                        'titulo': 'Totales por Columna',
                        'labels': stats.index.tolist(),
                        'datos': stats.values.tolist(),
                        'columna': 'resumen'
                    })
            
        except Exception as e:
            logger.error(f"Error generando datos de gráficos: {e}")
        
        return graficos
    
    def responder_pregunta(self, codigo_reporte: str, pregunta: str):
        """Responder pregunta sobre los datos usando RAG + LLM"""
        if not self.openai_client:
            return {'error': 'OpenAI no configurado'}
        
        try:
            # Buscar contexto relevante
            contexto = self.consultar_con_lenguaje_natural(codigo_reporte, pregunta, limite=5)
            
            # Obtener info del reporte
            reporte = self.db_manager.obtener_reporte(codigo_reporte)
            
            # Obtener estadísticas generales
            datos = self.db_manager.consultar_datos(codigo_reporte, limite=1000)
            df_datos = pd.DataFrame([d['datos'] for d in datos])
            
            # Detectar si se solicita un gráfico
            palabras_grafico = ['gráfico', 'grafico', 'gráfica', 'grafica', 'chart', 'visualiza', 'visualización', 'muestra', 'diagrama', 'top', 'ranking']
            solicita_grafico = any(palabra in pregunta.lower() for palabra in palabras_grafico)
            
            # Preparar estadísticas útiles del DataFrame
            stats_columnas = {}
            for col in df_datos.columns:
                if pd.api.types.is_numeric_dtype(df_datos[col]):
                    stats_columnas[col] = {
                        'tipo': 'numérico',
                        'total': float(df_datos[col].sum()),
                        'promedio': float(df_datos[col].mean()),
                        'max': float(df_datos[col].max()),
                        'min': float(df_datos[col].min())
                    }
                else:
                    valores_unicos = df_datos[col].nunique()
                    stats_columnas[col] = {
                        'tipo': 'texto',
                        'valores_unicos': int(valores_unicos),
                        'top_5': df_datos[col].value_counts().head(5).to_dict() if valores_unicos < 100 else None
                    }
            
            # Preparar prompt con contexto
            prompt = f"""Responde la siguiente pregunta sobre el reporte "{reporte['nombre']}":

PREGUNTA: {pregunta}

DATOS DISPONIBLES:
- Total de registros analizables: {len(datos)}
- Columnas: {', '.join(df_datos.columns.tolist())}

ESTADÍSTICAS POR COLUMNA:
{json.dumps(stats_columnas, indent=2, ensure_ascii=False, default=str)}

MUESTRA DE DATOS (primeros 5 registros):
{df_datos.head(5).to_dict('records')}

INSTRUCCIONES:
- Tienes acceso COMPLETO a {len(datos)} registros del reporte
- Puedes calcular sumas, promedios, conteos, agrupaciones, etc.
- Si necesitas hacer un análisis, HAZLO con los datos disponibles
- Si la pregunta pide gráficos o visualizaciones, confirma que puedes generarlos
- Sé específico con números y resultados
- Responde en español de forma clara y profesional"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """Eres un analista de datos experto con acceso COMPLETO a los datos del reporte.

CAPACIDADES CONFIRMADAS:
✅ Tienes acceso a TODOS los registros del reporte (no solo una muestra)
✅ Puedes calcular estadísticas: sumas, promedios, máximos, mínimos, conteos
✅ Puedes hacer agrupaciones y análisis complejos
✅ Puedes crear visualizaciones de datos usando formato de texto

FORMATO DE RESPUESTA:
❌ NUNCA describas el proceso paso a paso
❌ NUNCA muestres código Python ni menciones funciones técnicas
❌ NUNCA digas "voy a generar", "he generado", "puedes descargar"
✅ SOLO presenta los RESULTADOS finales
✅ Usa formato limpio: títulos, listas, tablas de texto, emojis
✅ Si piden gráfico: MUÉSTRALO en formato visual de texto (barras con caracteres, tablas)
✅ Si piden Excel: Entonces di "Preparando archivo Excel para descarga..."

EJEMPLO DE GRÁFICO EN TEXTO:
"📊 Distribución de Facturación por Estado:

Activo    ████████████████████ $45,234,567 (67%)
Inactivo  ██████████ $22,118,433 (33%)

💡 El estado 'Activo' representa dos tercios del valor total."

EJEMPLO INCORRECTO:
"He generado un gráfico de barras... puedes descargar el archivo Excel..."

INSTRUCCIONES CRÍTICAS:
- NUNCA digas "no tengo acceso" - SÍ tienes acceso completo
- NUNCA digas "necesito más información" - toda la info está en el contexto
- SIEMPRE realiza cálculos cuando se te pidan
- Responde SOLO con resultados, sin describir procesos
- Responde en español con números específicos y precisos"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            respuesta = response.choices[0].message.content
            
            resultado = {
                'pregunta': pregunta,
                'respuesta': respuesta,
                'contexto_usado': len(contexto['resultados']),
                'timestamp': datetime.now().isoformat()
            }
            
            # Generar gráfico si se solicitó
            if solicita_grafico:
                grafico = self._generar_grafico_personalizado(pregunta, df_datos)
                if grafico:
                    resultado['grafico'] = grafico
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error respondiendo pregunta: {e}")
            raise
    
    def _generar_grafico_personalizado(self, pregunta: str, df: pd.DataFrame):
        """Generar gráfico basado en la pregunta del usuario"""
        try:
            pregunta_lower = pregunta.lower()
            
            # Detectar tipo de gráfico solicitado
            tipo_grafico = 'bar'  # Por defecto barras
            if any(palabra in pregunta_lower for palabra in ['torta', 'pie', 'pastel', 'circular']):
                tipo_grafico = 'pie'
            
            # Detectar números solicitados (top 5, top 10, etc.)
            import re
            numeros = re.findall(r'\d+', pregunta)
            limite = int(numeros[0]) if numeros else 10
            limite = min(limite, 20)  # Máximo 20 elementos
            
            # Para gráfico de torta, limitar a máximo 8 segmentos
            if tipo_grafico == 'pie':
                limite = min(limite, 8)
            
            columna_objetivo = None
            valor_col = None
            agrupar_por_tiempo = None
            
            # Detectar agrupación temporal
            if any(palabra in pregunta_lower for palabra in ['semana', 'semanal', 'semanas']):
                agrupar_por_tiempo = 'semana'
            elif any(palabra in pregunta_lower for palabra in ['mes', 'mensual', 'meses']):
                agrupar_por_tiempo = 'mes'
            elif any(palabra in pregunta_lower for palabra in ['dia', 'diario', 'dias', 'día', 'días']):
                agrupar_por_tiempo = 'dia'
            elif any(palabra in pregunta_lower for palabra in ['año', 'anual', 'años']):
                agrupar_por_tiempo = 'año'
            
            # Palabras clave para detectar qué columna analizar
            palabras_busqueda = {
                'tipo': ['tipo', 'tipos', 'categoria', 'categoría', 'clase'],
                'cliente': ['cliente', 'razonsocial', 'razon', 'tercero', 'terceros'],
                'sede': ['sede', 'sedes', 'sucursal'],
                'estado': ['estado', 'estados', 'estatus'],
                'vendedor': ['vendedor', 'vendedora', 'comercial'],
                'producto': ['producto', 'productos', 'item', 'referencia'],
                'fecha': ['fecha', 'periodo']
            }
            
            # Buscar columna de fecha para agrupación temporal
            columna_fecha = None
            if agrupar_por_tiempo:
                for col in df.columns:
                    col_lower = col.lower()
                    if 'fecha' in col_lower or 'f_' in col_lower or 'date' in col_lower:
                        columna_fecha = col
                        break
            
            # Buscar columna de valor numérico para agrupar
            palabras_valor = ['factur', 'total', 'valor', 'venta', 'monto', 'precio', 'vr_']
            for col in df.columns:
                col_lower = col.lower()
                if pd.api.types.is_numeric_dtype(df[col]) and any(palabra in col_lower for palabra in palabras_valor):
                    valor_col = col
                    break
            
            # Si se pide agrupación temporal y hay columna de fecha
            if agrupar_por_tiempo and columna_fecha and columna_fecha in df.columns:
                try:
                    # Convertir a datetime si no lo es
                    if not pd.api.types.is_datetime64_any_dtype(df[columna_fecha]):
                        df[columna_fecha] = pd.to_datetime(df[columna_fecha], errors='coerce')
                    
                    # Agrupar según el período
                    if agrupar_por_tiempo == 'semana':
                        df['periodo'] = df[columna_fecha].dt.isocalendar().week.astype(str) + '-' + df[columna_fecha].dt.year.astype(str)
                        titulo_periodo = 'Semanas'
                    elif agrupar_por_tiempo == 'mes':
                        df['periodo'] = df[columna_fecha].dt.strftime('%Y-%m')
                        titulo_periodo = 'Meses'
                    elif agrupar_por_tiempo == 'dia':
                        df['periodo'] = df[columna_fecha].dt.strftime('%Y-%m-%d')
                        titulo_periodo = 'Días'
                    else:  # año
                        df['periodo'] = df[columna_fecha].dt.year.astype(str)
                        titulo_periodo = 'Años'
                    
                    if valor_col and valor_col in df.columns:
                        agrupado = df.groupby('periodo')[valor_col].sum().nlargest(limite)
                    else:
                        agrupado = df['periodo'].value_counts().head(limite)
                    
                    return {
                        'tipo': tipo_grafico,
                        'titulo': f'Facturación por {titulo_periodo}',
                        'labels': [str(x) for x in agrupado.index.tolist()],
                        'datos': agrupado.values.tolist(),
                        'columna': titulo_periodo
                    }
                except Exception as e:
                    logger.error(f"Error agrupando por tiempo: {e}")
                    # Continuar con la lógica normal
            
            # Buscar qué tipo de análisis pide el usuario
            for categoria, palabras in palabras_busqueda.items():
                if any(palabra in pregunta_lower for palabra in palabras):
                    # Buscar columna que coincida
                    for col in df.columns:
                        col_lower = col.lower()
                        if any(palabra in col_lower for palabra in palabras):
                            columna_objetivo = col
                            break
                    if columna_objetivo:
                        break
            
            # Si no encontró columna específica, buscar por nombre exacto en la pregunta
            if not columna_objetivo:
                for col in df.columns:
                    if col.lower() in pregunta_lower:
                        columna_objetivo = col
                        break
            
            # Si encontró columna objetivo
            if columna_objetivo and columna_objetivo in df.columns:
                # Si hay columna de valor, agrupar y sumar
                if valor_col and valor_col in df.columns:
                    agrupado = df.groupby(columna_objetivo)[valor_col].sum().nlargest(limite)
                    
                    return {
                        'tipo': tipo_grafico,
                        'titulo': f'Top {limite} por {columna_objetivo}',
                        'labels': [str(x) for x in agrupado.index.tolist()],
                        'datos': agrupado.values.tolist(),
                        'columna': columna_objetivo
                    }
                else:
                    # Si no hay valor, hacer conteo
                    conteo = df[columna_objetivo].value_counts().head(limite)
                    
                    return {
                        'tipo': tipo_grafico,
                        'titulo': f'Top {limite} - {columna_objetivo}',
                        'labels': [str(x) for x in conteo.index.tolist()],
                        'datos': conteo.values.tolist(),
                        'columna': columna_objetivo
                    }
            
            # Si no encontró nada específico, hacer gráfico de la primera columna de texto
            for col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    value_counts = df[col].value_counts().head(limite)
                    return {
                        'tipo': tipo_grafico,
                        'titulo': f'Top {limite} - {col}',
                        'labels': [str(x) for x in value_counts.index.tolist()],
                        'datos': value_counts.values.tolist(),
                        'columna': col
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error generando gráfico personalizado: {e}")
            return None
    
    def generar_informe_completo(self, codigo_reporte: str):
        """Generar informe completo con múltiples análisis"""
        try:
            informe = {
                'reporte': codigo_reporte,
                'fecha_generacion': datetime.now().isoformat(),
                'secciones': {}
            }
            
            # Análisis general
            if self.openai_client:
                informe['secciones']['analisis_general'] = self.generar_analisis_ia(codigo_reporte, 'general')
                informe['secciones']['tendencias'] = self.generar_analisis_ia(codigo_reporte, 'tendencias')
                informe['secciones']['anomalias'] = self.generar_analisis_ia(codigo_reporte, 'anomalias')
            
            # Estadísticas básicas
            datos = self.db_manager.consultar_datos(codigo_reporte, limite=10000)
            df_datos = pd.DataFrame([d['datos'] for d in datos])
            
            informe['estadisticas'] = {
                'total_registros': len(datos),
                'columnas': list(df_datos.columns),
                'tipos_datos': df_datos.dtypes.astype(str).to_dict(),
                'valores_nulos': df_datos.isnull().sum().to_dict(),
                'estadisticas_numericas': df_datos.describe().to_dict()
            }
            
            return informe
            
        except Exception as e:
            logger.error(f"Error generando informe: {e}")
            raise
    
    def generar_graficas_imagen(self, graficos_data: list, reporte_nombre: str = "Reporte") -> list:
        """
        Generar gráficas como imágenes PNG a partir de datos de gráficos
        Retorna lista de BytesIO con las imágenes generadas
        """
        imagenes = []
        
        try:
            for idx, grafico in enumerate(graficos_data):
                # Crear nueva figura
                fig, ax = plt.subplots(figsize=(10, 6))
                
                tipo = grafico.get('tipo', 'bar')
                titulo = grafico.get('titulo', f'Gráfico {idx + 1}')
                labels = grafico.get('labels', [])
                datos = grafico.get('datos', [])
                
                if not labels or not datos:
                    continue
                
                # Limitar cantidad de elementos para mejor visualización
                max_elementos = 15
                if len(labels) > max_elementos:
                    labels = labels[:max_elementos]
                    datos = datos[:max_elementos]
                
                if tipo == 'bar':
                    # Gráfico de barras
                    colors = sns.color_palette("husl", len(labels))
                    bars = ax.bar(range(len(labels)), datos, color=colors, edgecolor='black', linewidth=0.5)
                    ax.set_xticks(range(len(labels)))
                    ax.set_xticklabels(labels, rotation=45, ha='right')
                    ax.set_ylabel('Valor')
                    
                    # Agregar valores en las barras
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{height:,.0f}',
                               ha='center', va='bottom', fontsize=9)
                
                elif tipo == 'pie':
                    # Gráfico de torta
                    colors = sns.color_palette("pastel", len(labels))
                    wedges, texts, autotexts = ax.pie(datos, labels=labels, autopct='%1.1f%%',
                                                       colors=colors, startangle=90)
                    # Mejorar legibilidad
                    for text in texts:
                        text.set_fontsize(9)
                    for autotext in autotexts:
                        autotext.set_color('white')
                        autotext.set_fontsize(8)
                        autotext.set_weight('bold')
                
                elif tipo == 'line':
                    # Gráfico de líneas
                    ax.plot(range(len(labels)), datos, marker='o', linewidth=2, 
                           color='#4285F4', markersize=8)
                    ax.set_xticks(range(len(labels)))
                    ax.set_xticklabels(labels, rotation=45, ha='right')
                    ax.set_ylabel('Valor')
                    ax.grid(True, alpha=0.3)
                    
                    # Agregar valores en los puntos
                    for i, v in enumerate(datos):
                        ax.text(i, v, f'{v:,.0f}', ha='center', va='bottom', fontsize=9)
                
                # Título y diseño
                ax.set_title(titulo, fontsize=14, fontweight='bold', pad=20)
                plt.tight_layout()
                
                # Guardar en BytesIO
                img_buffer = BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                           facecolor='white', edgecolor='none')
                img_buffer.seek(0)
                
                imagenes.append({
                    'titulo': titulo,
                    'buffer': img_buffer,
                    'tipo': tipo
                })
                
                # Cerrar figura para liberar memoria
                plt.close(fig)
            
            logger.info(f"Generadas {len(imagenes)} gráficas exitosamente")
            return imagenes
            
        except Exception as e:
            logger.error(f"Error generando gráficas: {e}")
            return []
    
    def generar_grafica_base64(self, grafico_data: dict) -> str:
        """
        Generar una gráfica y retornarla como base64 para incrustar en HTML
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            tipo = grafico_data.get('tipo', 'bar')
            titulo = grafico_data.get('titulo', 'Gráfico')
            labels = grafico_data.get('labels', [])
            datos = grafico_data.get('datos', [])
            
            if not labels or not datos:
                plt.close(fig)
                return None
            
            # Limitar elementos
            max_elementos = 15
            if len(labels) > max_elementos:
                labels = labels[:max_elementos]
                datos = datos[:max_elementos]
            
            if tipo == 'bar':
                colors = sns.color_palette("husl", len(labels))
                bars = ax.bar(range(len(labels)), datos, color=colors, edgecolor='black', linewidth=0.5)
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=45, ha='right')
                ax.set_ylabel('Valor')
                
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:,.0f}', ha='center', va='bottom', fontsize=9)
            
            elif tipo == 'pie':
                colors = sns.color_palette("pastel", len(labels))
                wedges, texts, autotexts = ax.pie(datos, labels=labels, autopct='%1.1f%%',
                                                   colors=colors, startangle=90)
                for text in texts:
                    text.set_fontsize(9)
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(8)
                    autotext.set_weight('bold')
            
            ax.set_title(titulo, fontsize=14, fontweight='bold', pad=20)
            plt.tight_layout()
            
            # Convertir a base64
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=120, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            img_buffer.seek(0)
            
            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            plt.close(fig)
            
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Error generando gráfica base64: {e}")
            return None
    
    def generar_informe_personalizado(self, codigo_reporte: str, solicitud: str):
        """
        Generar informe personalizado basado en solicitud en lenguaje natural
        
        Ejemplos de solicitud:
        - "facturación semanal agrupada por tercero"
        - "ventas mensuales por producto"
        - "gastos por categoría en el último trimestre"
        """
        try:
            # Obtener datos del reporte
            reporte = self.db_manager.obtener_reporte(codigo_reporte)
            if not reporte:
                raise ValueError(f"Reporte {codigo_reporte} no encontrado")
            
            datos = self.db_manager.consultar_datos(codigo_reporte, limite=10000)
            if not datos:
                raise ValueError("No hay datos disponibles para generar el informe")
            
            df = pd.DataFrame([d['datos'] for d in datos])
            
            # Interpretar la solicitud usando IA
            if self.openai_client:
                analisis_solicitud = self._interpretar_solicitud_informe(solicitud, df.columns.tolist())
            else:
                # Interpretación básica sin IA
                analisis_solicitud = self._interpretar_solicitud_basica(solicitud, df.columns.tolist())
            
            # Agrupar y procesar datos según la solicitud
            df_procesado, agrupaciones = self._procesar_datos_segun_solicitud(df, analisis_solicitud)
            
            # Generar gráficos relevantes
            graficos = self._generar_graficos_para_informe(df_procesado, agrupaciones, analisis_solicitud)
            
            # Generar resumen ejecutivo con IA
            resumen_ejecutivo = ""
            if self.openai_client:
                resumen_ejecutivo = self._generar_resumen_ejecutivo(
                    reporte['nombre'], 
                    solicitud, 
                    df_procesado, 
                    agrupaciones
                )
            
            return {
                'reporte': reporte['nombre'],
                'codigo': codigo_reporte,
                'solicitud': solicitud,
                'fecha_generacion': datetime.now().isoformat(),
                'total_registros': len(datos),
                'registros_procesados': len(df_procesado),
                'agrupaciones': agrupaciones,
                'analisis_solicitud': analisis_solicitud,
                'datos_procesados': df_procesado.to_dict('records'),
                'graficos': graficos,
                'resumen_ejecutivo': resumen_ejecutivo,
                'estadisticas': {
                    'min': df_procesado.select_dtypes(include=['number']).min().to_dict() if len(df_procesado.select_dtypes(include=['number']).columns) > 0 else {},
                    'max': df_procesado.select_dtypes(include=['number']).max().to_dict() if len(df_procesado.select_dtypes(include=['number']).columns) > 0 else {},
                    'promedio': df_procesado.select_dtypes(include=['number']).mean().to_dict() if len(df_procesado.select_dtypes(include=['number']).columns) > 0 else {},
                    'total': df_procesado.select_dtypes(include=['number']).sum().to_dict() if len(df_procesado.select_dtypes(include=['number']).columns) > 0 else {}
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando informe personalizado: {e}")
            raise
    
    def _interpretar_solicitud_informe(self, solicitud: str, columnas_disponibles: list):
        """Usar IA para interpretar qué quiere el usuario"""
        try:
            prompt = f"""Analiza la siguiente solicitud de informe y extrae:
1. Campo por el cual agrupar (debe ser uno de: {', '.join(columnas_disponibles)})
2. Periodo temporal (diario, semanal, mensual, trimestral, anual, o ninguno)
3. Métricas a calcular (suma, promedio, conteo, etc.)
4. Tipo de visualización sugerida (barras, líneas, pastel, tabla)

Solicitud: "{solicitud}"

Columnas disponibles: {', '.join(columnas_disponibles)}

Responde en formato JSON:
{{
    "campo_agrupacion": "nombre_del_campo",
    "periodo_temporal": "semanal|mensual|ninguno",
    "metricas": ["suma", "conteo"],
    "visualizacion": "barras",
    "campo_temporal": "nombre_campo_fecha_si_existe",
    "campo_valor": "nombre_campo_numerico_principal"
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """Eres un asistente especializado en interpretar solicitudes de informes.
                    
                    El sistema puede generar:
                    - Gráficos de barras, torta, líneas para cualquier métrica
                    - Reportes Excel profesionales con 4 hojas (Resumen, Datos, Gráficos, Estadísticas)
                    - Análisis agrupados por cualquier campo
                    - Exportación y envío por correo
                    
                    Extrae los parámetros estructurados de la solicitud del usuario."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error interpretando solicitud con IA: {e}")
            return self._interpretar_solicitud_basica(solicitud, columnas_disponibles)
    
    def _interpretar_solicitud_basica(self, solicitud: str, columnas_disponibles: list):
        """Interpretación básica sin IA"""
        solicitud_lower = solicitud.lower()
        
        # Detectar periodo
        periodo = "ninguno"
        if "semanal" in solicitud_lower or "semana" in solicitud_lower:
            periodo = "semanal"
        elif "mensual" in solicitud_lower or "mes" in solicitud_lower:
            periodo = "mensual"
        elif "diario" in solicitud_lower or "dia" in solicitud_lower or "día" in solicitud_lower:
            periodo = "diario"
        
        # Detectar campo de agrupación
        campo_agrupacion = None
        for col in columnas_disponibles:
            if col.lower() in solicitud_lower:
                campo_agrupacion = col
                break
        
        # Si menciona "tercero", "cliente", "proveedor"
        if not campo_agrupacion:
            for col in columnas_disponibles:
                if any(palabra in col.lower() for palabra in ['tercero', 'cliente', 'proveedor', 'nombre', 'razon']):
                    campo_agrupacion = col
                    break
        
        # Detectar campo de valor
        campo_valor = None
        for col in columnas_disponibles:
            if any(palabra in col.lower() for palabra in ['total', 'valor', 'monto', 'importe', 'suma']):
                campo_valor = col
                break
        
        # Detectar campo temporal
        campo_temporal = None
        for col in columnas_disponibles:
            if 'fecha' in col.lower() or 'f_' in col.lower():
                campo_temporal =col
                break
        
        return {
            "campo_agrupacion": campo_agrupacion or columnas_disponibles[0],
            "periodo_temporal": periodo,
            "metricas": ["suma", "conteo"],
            "visualizacion": "barras",
            "campo_temporal": campo_temporal,
            "campo_valor": campo_valor
        }
    
    def _procesar_datos_segun_solicitud(self, df: pd.DataFrame, analisis: dict):
        """Procesar y agrupar datos según el análisis de la solicitud"""
        try:
            campo_agrupacion = analisis.get('campo_agrupacion')
            campo_valor = analisis.get('campo_valor')
            campo_temporal = analisis.get('campo_temporal')
            periodo = analisis.get('periodo_temporal', 'ninguno')
            
            # Validar que los campos existan
            if campo_agrupacion not in df.columns:
                campo_agrupacion = df.columns[0]
            
            # Si hay campo de valor numérico
            if campo_valor and campo_valor in df.columns:
                # Convertir a numérico si no lo es
                df[campo_valor] = pd.to_numeric(df[campo_valor], errors='coerce')
                
                # Agrupar y sumar
                df_agrupado = df.groupby(campo_agrupacion)[campo_valor].agg(['sum', 'count', 'mean']).reset_index()
                df_agrupado.columns = [campo_agrupacion, 'Total', 'Cantidad', 'Promedio']
                df_agrupado = df_agrupado.sort_values('Total', ascending=False)
                
                agrupaciones = {
                    'tipo': 'valor_numerico',
                    'campo_principal': campo_agrupacion,
                    'campo_valor': campo_valor,
                    'total_grupos': len(df_agrupado)
                }
            else:
                # Solo contar ocurrencias
                df_agrupado = df.groupby(campo_agrupacion).size().reset_index(name='Cantidad')
                df_agrupado = df_agrupado.sort_values('Cantidad', ascending=False)
                
                agrupaciones = {
                    'tipo': 'conteo',
                    'campo_principal': campo_agrupacion,
                    'total_grupos': len(df_agrupado)
                }
            
            # Si hay periodo temporal, agregar análisis temporal
            if periodo != 'ninguno' and campo_temporal and campo_temporal in df.columns:
                try:
                    df[campo_temporal] = pd.to_datetime(df[campo_temporal], errors='coerce')
                    df = df.dropna(subset=[campo_temporal])
                    
                    if periodo == 'semanal':
                        df['periodo'] = df[campo_temporal].dt.to_period('W').astype(str)
                    elif periodo == 'mensual':
                        df['periodo'] = df[campo_temporal].dt.to_period('M').astype(str)
                    elif periodo == 'diario':
                        df['periodo'] = df[campo_temporal].dt.date.astype(str)
                    
                    if 'periodo' in df.columns:
                        agrupaciones['tiene_periodo_temporal'] = True
                        agrupaciones['periodo'] = periodo
                        
                except Exception as e:
                    logger.warning(f"No se pudo procesar campo temporal: {e}")
            
            return df_agrupado, agrupaciones
            
        except Exception as e:
            logger.error(f"Error procesando datos: {e}")
            # Fallback: retornar datos originales
            return df.head(100), {'tipo': 'sin_agrupacion'}
    
    def _generar_graficos_para_informe(self, df: pd.DataFrame, agrupaciones: dict, analisis: dict):
        """Generar gráficos relevantes para el informe"""
        graficos = []
        
        try:
            campo_principal = agrupaciones.get('campo_principal', df.columns[0])
            
            # Limitar a top 15 para visualización
            df_top = df.head(15)
            
            # Gráfico principal (barras)
            if 'Total' in df_top.columns:
                graficos.append({
                    'tipo': 'bar',
                    'titulo': f'Top 15 {campo_principal} por Total',
                    'labels': df_top[campo_principal].astype(str).tolist(),
                    'datos': df_top['Total'].tolist(),
                    'columna': 'Total'
                })
                
                # Gráfico de pastel para distribución (solo top 10)
                df_pie = df.head(10)
                if len(df_pie) > 1:
                    graficos.append({
                        'tipo': 'pie',
                        'titulo': f'Distribución Top 10 - {campo_principal}',
                        'labels': df_pie[campo_principal].astype(str).tolist(),
                        'datos': df_pie['Total'].tolist(),
                        'columna': 'Total'
                    })
            
            elif 'Cantidad' in df_top.columns:
                graficos.append({
                    'tipo': 'bar',
                    'titulo': f'Top 15 {campo_principal} por Cantidad',
                    'labels': df_top[campo_principal].astype(str).tolist(),
                    'datos': df_top['Cantidad'].tolist(),
                    'columna': 'Cantidad'
                })
            
            # Si hay promedio, agregar gráfico
            if 'Promedio' in df_top.columns:
                graficos.append({
                    'tipo': 'bar',
                    'titulo': f'Promedio por {campo_principal}',
                    'labels': df_top[campo_principal].astype(str).tolist(),
                    'datos': df_top['Promedio'].tolist(),
                    'columna': 'Promedio'
                })
            
        except Exception as e:
            logger.error(f"Error generando gráficos para informe: {e}")
        
        return graficos
    
    def _generar_resumen_ejecutivo(self, nombre_reporte: str, solicitud: str, df: pd.DataFrame, agrupaciones: dict):
        """Generar resumen ejecutivo con IA"""
        try:
            # Preparar estadísticas para la IA
            stats = {
                'total_grupos': len(df),
                'top_5': df.head(5).to_dict('records')
            }
            
            if 'Total' in df.columns:
                stats['total_general'] = float(df['Total'].sum())
                stats['promedio_general'] = float(df['Total'].mean())
                stats['top_contribuidor'] = {
                    'nombre': str(df.iloc[0][agrupaciones['campo_principal']]),
                    'valor': float(df.iloc[0]['Total'])
                }
            
            prompt = f"""Genera un resumen ejecutivo CONCISO y ENFOCADO EN RESULTADOS para el siguiente informe:

Reporte: {nombre_reporte}
Solicitud del usuario: {solicitud}

Estadísticas:
{json.dumps(stats, indent=2, default=str)}

⚠️ FORMATO REQUERIDO:
- SOLO presenta hallazgos y resultados finales
- NO menciones el archivo Excel ni proceso de generación
- NO uses frases como "he generado", "se incluye", "archivo adjunto"
- Usa lenguaje ejecutivo directo: "El análisis muestra que..."

Estructura requerida:
1. 📊 HALLAZGOS PRINCIPALES (2-3 puntos clave con datos)
2. 💡 INSIGHTS (tendencias o patrones identificados)
3. 🎯 RECOMENDACIONES (1-2 acciones sugeridas)

Máximo 250 palabras. Responde en español."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """Eres un analista de negocios senior que presenta solo RESULTADOS finales.

PROHIBIDO mencionar:
❌ "He generado un gráfico..."
❌ "Puedes descargar el archivo..."
❌ "El archivo Excel incluye..."
❌ Cualquier referencia a procesos técnicos

OBLIGATORIO:
✅ Presentar solo hallazgos y datos
✅ Usar lenguaje ejecutivo conciso
✅ Enfocarse en insights de negocio
✅ Incluir números específicos
                    
Genera resúmenes ejecutivos 100% enfocados en resultados, sin mencionar procesos ni archivos."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generando resumen ejecutivo: {e}")
            return "Resumen ejecutivo no disponible."
    
    # ========== SISTEMA DE VALIDACIÓN Y ACLARACIONES ==========
    
    def validar_reporte_con_ia(self, campos_config: List[Dict]) -> Dict:
        """
        Valida la configuración de campos del reporte con IA
        Detecta campos ambiguos o que requieren aclaración
        
        Args:
            campos_config: Lista de configuraciones de campos del reporte
            
        Returns:
            Dict con:
                - aprobado: bool
                - puntuacion_claridad: float (0-100)
                - campos_dudosos: List[Dict] con campos que necesitan aclaración
                - sugerencias: List[str] con sugerencias generales
        """
        try:
            # Construir contexto de los campos
            campos_info = []
            for campo in campos_config:
                campos_info.append({
                    'nombre': campo.get('nombre', ''),
                    'tipo': campo.get('tipo', ''),
                    'descripcion': campo.get('descripcion', ''),
                    'obligatorio': campo.get('obligatorio', False)
                })
            
            # Prompt para validación
            prompt = f'''Eres un validador experto de configuraciones de reportes. 
            
Analiza la siguiente configuración de campos y determina:
1. Si algún nombre de campo es ambiguo o poco claro
2. Si las descripciones son suficientes
3. Puntuación de claridad general (0-100)
4. Qué campos necesitan aclaración del usuario

Campos a validar:
{json.dumps(campos_info, indent=2, ensure_ascii=False)}

Responde ÚNICAMENTE con JSON válido en este formato:
{{
    "aprobado": true/false,
    "puntuacion_claridad": 0-100,
    "campos_dudosos": [
        {{
            "nombre": "nombre_campo",
            "razon": "por qué es ambiguo",
            "severidad": "alta/media/baja"
        }}
    ],
    "sugerencias": ["sugerencia 1", "sugerencia 2"]
}}'''

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un validador experto. Respondes SOLO con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            resultado = json.loads(response.choices[0].message.content)
            logger.info(f"Validación completada. Puntuación: {resultado.get('puntuacion_claridad', 0)}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error validando reporte con IA: {e}")
            return {
                "aprobado": True,
                "puntuacion_claridad": 50,
                "campos_dudosos": [],
                "sugerencias": [f"Error en validación: {str(e)}"]
            }
    
    def generar_pregunta_aclaracion(self, nombre_campo: str, tipo_campo: str, 
                                   descripcion: str = "", razon: str = "") -> str:
        """
        Genera una pregunta clara para solicitar aclaración sobre un campo
        
        Args:
            nombre_campo: Nombre del campo
            tipo_campo: Tipo de dato (texto, número, fecha, etc.)
            descripcion: Descripción actual del campo
            razon: Razón por la que se solicita aclaración
            
        Returns:
            str: Pregunta formulada para el usuario
        """
        try:
            prompt = f'''Genera una pregunta ESPECÍFICA y CLARA para solicitar aclaración sobre un campo de reporte.

Campo: {nombre_campo}
Tipo: {tipo_campo}
Descripción actual: {descripcion or "Sin descripción"}
Razón de la duda: {razon}

La pregunta debe:
- Ser directa y fácil de entender
- Solicitar información concreta
- Ayudar a eliminar ambigüedad
- Ser breve (máximo 2 líneas)

Ejemplo buenos:
- "¿Qué significa 'estado' en este contexto? ¿Se refiere al estado del proceso, ubicación geográfica, o condición del registro?"
- "El campo 'valor' ¿representa un monto en pesos, porcentaje, o cantidad de unidades?"

Genera SOLO la pregunta, sin explicaciones adicionales.'''

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Generas preguntas claras y concisas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            pregunta = response.choices[0].message.content.strip()
            logger.info(f"Pregunta generada para campo {nombre_campo}")
            
            return pregunta
            
        except Exception as e:
            logger.error(f"Error generando pregunta: {e}")
            return f"¿Podrías explicar qué información debe contener el campo '{nombre_campo}'?"
    
    def obtener_conocimiento_previo(self, nombre_campo: str, tipo_aprendizaje: str = 'aclaracion_campo') -> Optional[str]:
        """
        Busca conocimiento previo en la base de aprendizaje de IA
        
        Args:
            nombre_campo: Nombre del campo a buscar
            tipo_aprendizaje: Tipo de conocimiento a buscar
            
        Returns:
            str: Respuesta mejorada si existe, None si no hay conocimiento previo
        """
        try:
            conn = self.db_manager.get_connection()
            cur = conn.cursor()
            
            cur.execute('''
                SELECT respuesta_mejorada, efectividad
                FROM ia_aprendizaje
                WHERE tipo_aprendizaje = %s
                  AND contexto ILIKE %s
                  AND activo = TRUE
                ORDER BY efectividad DESC, fecha_creacion DESC
                LIMIT 1
            ''', (tipo_aprendizaje, f'%{nombre_campo}%'))
            
            row = cur.fetchone()
            
            if row:
                logger.info(f"Conocimiento previo encontrado para {nombre_campo}")
                return row[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error buscando conocimiento previo: {e}")
            return None
        finally:
            cur.close()
            conn.close()
