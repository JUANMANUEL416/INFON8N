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
        
        # 🆕 Sistema de memoria conversacional
        self.conversaciones = {}  # {session_id: [{role, content}]}
        self.max_historial = 10   # Últimos 10 mensajes por sesión
    
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
    
    # ============================================
    # SISTEMA DE MEMORIA CONVERSACIONAL
    # ============================================
    
    def obtener_historial(self, session_id: str) -> List[Dict]:
        """Obtener historial de conversación de una sesión"""
        return self.conversaciones.get(session_id, [])
    
    def agregar_mensaje(self, session_id: str, role: str, content: str):
        """Agregar mensaje al historial de conversación"""
        if session_id not in self.conversaciones:
            self.conversaciones[session_id] = []
        
        self.conversaciones[session_id].append({
            "role": role,
            "content": content
        })
        
        # Mantener solo los últimos N mensajes
        if len(self.conversaciones[session_id]) > self.max_historial * 2:  # *2 porque user+assistant
            self.conversaciones[session_id] = self.conversaciones[session_id][-self.max_historial*2:]
        
        logger.info(f"Mensaje agregado a sesión {session_id}. Total: {len(self.conversaciones[session_id])}")
    
    def limpiar_sesion(self, session_id: str):
        """Limpiar historial de una sesión"""
        if session_id in self.conversaciones:
            del self.conversaciones[session_id]
            logger.info(f"Sesión {session_id} limpiada")
    
    # ============================================
    # FUNCIONES EJECUTABLES (FUNCTION CALLING)
    # ============================================
    
    def _calcular_total_campo(self, codigo_reporte: str, campo: str, fecha_inicio: str = None, fecha_fin: str = None) -> Dict:
        """Calcular suma total de un campo numérico"""
        try:
            datos = self.db_manager.consultar_datos_filtrado(
                codigo_reporte,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                limite=10000
            )
            if not datos:
                return {"error": "No hay datos disponibles"}
            
            df = pd.DataFrame([d['datos'] for d in datos])
            
            if campo not in df.columns:
                return {"error": f"Campo '{campo}' no existe"}
            
            if not pd.api.types.is_numeric_dtype(df[campo]):
                return {"error": f"Campo '{campo}' no es numérico"}
            
            total = float(df[campo].sum())
            promedio = float(df[campo].mean())
            maximo = float(df[campo].max())
            minimo = float(df[campo].min())
            
            return {
                "campo": campo,
                "total": total,
                "promedio": promedio,
                "maximo": maximo,
                "minimo": minimo,
                "registros": len(datos),
                "periodo": f"{fecha_inicio or 'inicio'} a {fecha_fin or 'fin'}"
            }
        except Exception as e:
            logger.error(f"Error calculando total: {e}")
            return {"error": str(e)}
    
    def _contar_registros(self, codigo_reporte: str, campo: str = None, valor: str = None, fecha_inicio: str = None, fecha_fin: str = None) -> Dict:
        """Contar registros con filtros opcionales"""
        try:
            datos = self.db_manager.consultar_datos_filtrado(
                codigo_reporte,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                limite=10000
            )
            
            if not datos:
                return {"total": 0, "registros": 0}
            
            df = pd.DataFrame([d['datos'] for d in datos])
            
            if campo and valor:
                filtrados = df[df[campo] == valor]
                return {
                    "total": len(filtrados),
                    "registros": len(datos),
                    "filtro": f"{campo} = {valor}",
                    "porcentaje": round(len(filtrados) / len(datos) * 100, 2)
                }
            
            return {"total": len(datos), "registros": len(datos)}
        except Exception as e:
            logger.error(f"Error contando registros: {e}")
            return {"error": str(e)}
    
    def _agrupar_por_campo(self, codigo_reporte: str, campo_agrupar: str, campo_sumar: str = None, top: int = 10) -> Dict:
        """Agrupar datos por un campo y opcionalmente sumar otro"""
        try:
            datos = self.db_manager.consultar_datos(codigo_reporte, limite=10000)
            if not datos:
                return {"error": "No hay datos disponibles"}
            
            df = pd.DataFrame([d['datos'] for d in datos])
            
            if campo_agrupar not in df.columns:
                return {"error": f"Campo '{campo_agrupar}' no existe"}
            
            if campo_sumar:
                if campo_sumar not in df.columns:
                    return {"error": f"Campo '{campo_sumar}' no existe"}
                
                resultado = df.groupby(campo_agrupar)[campo_sumar].sum().sort_values(ascending=False).head(top)
                return {
                    "agrupado_por": campo_agrupar,
                    "campo_sumado": campo_sumar,
                    "top": top,
                    "resultados": resultado.to_dict()
                }
            else:
                resultado = df[campo_agrupar].value_counts().head(top)
                return {
                    "agrupado_por": campo_agrupar,
                    "top": top,
                    "resultados": resultado.to_dict()
                }
        except Exception as e:
            logger.error(f"Error agrupando: {e}")
            return {"error": str(e)}
    
    def _comparar_periodos(self, codigo_reporte: str, campo: str, periodo1_inicio: str, periodo1_fin: str, 
                          periodo2_inicio: str, periodo2_fin: str) -> Dict:
        """Comparar un campo entre dos períodos"""
        try:
            # Período 1
            datos1 = self.db_manager.consultar_datos_filtrado(
                codigo_reporte,
                fecha_inicio=periodo1_inicio,
                fecha_fin=periodo1_fin,
                limite=10000
            )
            # Período 2
            datos2 = self.db_manager.consultar_datos_filtrado(
                codigo_reporte,
                fecha_inicio=periodo2_inicio,
                fecha_fin=periodo2_fin,
                limite=10000
            )
            
            if not datos1 or not datos2:
                return {"error": "No hay datos suficientes para comparar"}
            
            df1 = pd.DataFrame([d['datos'] for d in datos1])
            df2 = pd.DataFrame([d['datos'] for d in datos2])
            
            if campo not in df1.columns or campo not in df2.columns:
                return {"error": f"Campo '{campo}' no existe"}
            
            total1 = float(df1[campo].sum())
            total2 = float(df2[campo].sum())
            diferencia = total2 - total1
            porcentaje_cambio = ((total2 - total1) / total1 * 100) if total1 > 0 else 0
            
            return {
                "campo": campo,
                "periodo1": {"inicio": periodo1_inicio, "fin": periodo1_fin, "total": total1, "registros": len(datos1)},
                "periodo2": {"inicio": periodo2_inicio, "fin": periodo2_fin, "total": total2, "registros": len(datos2)},
                "diferencia": diferencia,
                "porcentaje_cambio": round(porcentaje_cambio, 2),
                "tendencia": "↑" if diferencia > 0 else "↓" if diferencia < 0 else "→"
            }
        except Exception as e:
            logger.error(f"Error comparando períodos: {e}")
            return {"error": str(e)}
    
    def _obtener_estadisticas(self, codigo_reporte: str, campo: str) -> Dict:
        """Obtener estadísticas detalladas de un campo"""
        try:
            datos = self.db_manager.consultar_datos(codigo_reporte, limite=10000)
            if not datos:
                return {"error": "No hay datos disponibles"}
            
            df = pd.DataFrame([d['datos'] for d in datos])
            
            if campo not in df.columns:
                return {"error": f"Campo '{campo}' no existe"}
            
            if pd.api.types.is_numeric_dtype(df[campo]):
                return {
                    "campo": campo,
                    "tipo": "numérico",
                    "total": float(df[campo].sum()),
                    "promedio": float(df[campo].mean()),
                    "mediana": float(df[campo].median()),
                    "desviacion_std": float(df[campo].std()),
                    "min": float(df[campo].min()),
                    "max": float(df[campo].max()),
                    "q25": float(df[campo].quantile(0.25)),
                    "q75": float(df[campo].quantile(0.75))
                }
            else:
                return {
                    "campo": campo,
                    "tipo": "categórico",
                    "valores_unicos": int(df[campo].nunique()),
                    "total_registros": len(df),
                    "top_5": df[campo].value_counts().head(5).to_dict()
                }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {"error": str(e)}
    
    def _get_available_functions(self):
        """Definir funciones disponibles para OpenAI Function Calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "calcular_total_campo",
                    "description": "Calcula el total, promedio, máximo y mínimo de un campo numérico. Útil para preguntas como '¿cuál es el total facturado?' o '¿cuánto se vendió?'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campo": {
                                "type": "string",
                                "description": "Nombre del campo numérico a sumar (ej: monto, vr_total, valorservicios)"
                            },
                            "fecha_inicio": {
                                "type": "string",
                                "description": "Fecha de inicio en formato YYYY-MM-DD (opcional)"
                            },
                            "fecha_fin": {
                                "type": "string",
                                "description": "Fecha de fin en formato YYYY-MM-DD (opcional)"
                            }
                        },
                        "required": ["campo"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "contar_registros",
                    "description": "Cuenta registros totales o filtrados por un valor específico",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campo": {
                                "type": "string",
                                "description": "Campo por el cual filtrar (opcional)"
                            },
                            "valor": {
                                "type": "string",
                                "description": "Valor a buscar en el campo (opcional)"
                            },
                            "fecha_inicio": {
                                "type": "string",
                                "description": "Fecha de inicio (opcional)"
                            },
                            "fecha_fin": {
                                "type": "string",
                                "description": "Fecha de fin (opcional)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "agrupar_por_campo",
                    "description": "Agrupa datos por un campo y opcionalmente suma otro. Útil para rankings y top N",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campo_agrupar": {
                                "type": "string",
                                "description": "Campo por el cual agrupar (ej: cliente, estado, tipo)"
                            },
                            "campo_sumar": {
                                "type": "string",
                                "description": "Campo numérico a sumar por cada grupo (opcional)"
                            },
                            "top": {
                                "type": "integer",
                                "description": "Número de resultados a retornar (default: 10)"
                            }
                        },
                        "required": ["campo_agrupar"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "comparar_periodos",
                    "description": "Compara un campo numérico entre dos períodos de tiempo",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campo": {
                                "type": "string",
                                "description": "Campo numérico a comparar"
                            },
                            "periodo1_inicio": {
                                "type": "string",
                                "description": "Fecha inicio período 1 (YYYY-MM-DD)"
                            },
                            "periodo1_fin": {
                                "type": "string",
                                "description": "Fecha fin período 1 (YYYY-MM-DD)"
                            },
                            "periodo2_inicio": {
                                "type": "string",
                                "description": "Fecha inicio período 2 (YYYY-MM-DD)"
                            },
                            "periodo2_fin": {
                                "type": "string",
                                "description": "Fecha fin período 2 (YYYY-MM-DD)"
                            }
                        },
                        "required": ["campo", "periodo1_inicio", "periodo1_fin", "periodo2_inicio", "periodo2_fin"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "obtener_estadisticas",
                    "description": "Obtiene estadísticas detalladas de un campo (media, mediana, desviación, cuartiles)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campo": {
                                "type": "string",
                                "description": "Campo del cual obtener estadísticas"
                            }
                        },
                        "required": ["campo"]
                    }
                }
            }
        ]
    
    def _ejecutar_funcion(self, nombre_funcion: str, argumentos: Dict, codigo_reporte: str) -> Dict:
        """Ejecutar la función correspondiente"""
        funciones = {
            "calcular_total_campo": lambda args: self._calcular_total_campo(codigo_reporte, **args),
            "contar_registros": lambda args: self._contar_registros(codigo_reporte, **args),
            "agrupar_por_campo": lambda args: self._agrupar_por_campo(codigo_reporte, **args),
            "comparar_periodos": lambda args: self._comparar_periodos(codigo_reporte, **args),
            "obtener_estadisticas": lambda args: self._obtener_estadisticas(codigo_reporte, **args)
        }
        
        if nombre_funcion in funciones:
            return funciones[nombre_funcion](argumentos)
        else:
            return {"error": f"Función {nombre_funcion} no encontrada"}
    

    def indexar_datos_reporte(self, codigo_reporte: str):
        """Indexar datos de un reporte en ChromaDB para búsqueda semántica"""
        try:
            # Obtener configuración del reporte
            reporte = self.db_manager.obtener_reporte(codigo_reporte)
            if not reporte:
                raise ValueError(f"Reporte {codigo_reporte} no encontrado")
            
            # Extraer contexto del reporte
            contexto_reporte = reporte.get('contexto', '')
            descripcion_reporte = reporte.get('descripcion', '')
            campos_config = reporte.get('campos', [])
            # Parsear JSON si viene como cadena
            if isinstance(campos_config, str):
                try:
                    campos_config = json.loads(campos_config)
                except Exception:
                    logger.warning("campos_config no es JSON válido; usando lista vacía")
                    campos_config = []

            # Fallback: si no hay configuración de campos, inferir desde datos
            if not campos_config:
                try:
                    muestra = self.db_manager.consultar_datos(codigo_reporte, limite=1)
                    if muestra and isinstance(muestra, list):
                        datos_dict = muestra[0].get('datos', {})
                        campos_config = [
                            {
                                'nombre': k,
                                'etiqueta': k,
                                'descripcion': 'Campo inferido desde datos',
                                'tipo_dato': 'texto'
                            } for k in datos_dict.keys()
                        ]
                        logger.info(f"Campos inferidos: {[c['nombre'] for c in campos_config]}")
                except Exception as e_inf:
                    logger.warning(f"No se pudo inferir campos desde datos: {e_inf}")
            
            # Construir documentación de campos
            docs_campos = {}
            for campo in campos_config:
                nombre_campo = campo.get('nombre', '')
                docs_campos[nombre_campo] = {
                    'etiqueta': campo.get('etiqueta', nombre_campo),
                    'descripcion': campo.get('descripcion', ''),
                    'tipo': campo.get('tipo_dato', 'texto'),
                    'ejemplo': campo.get('ejemplo', '')
                }
            
            # Obtener datos
            datos = self.db_manager.consultar_datos(codigo_reporte, limite=5000)
            
            if not datos:
                logger.info(f"No hay datos para indexar en {codigo_reporte}")
                return {'indexed': 0}
            
            # Crear o obtener colección
            collection_name = f"reporte_{codigo_reporte.replace(' ', '_')}"
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "reporte": codigo_reporte,
                    "nombre": reporte.get('nombre', ''),
                    "contexto": contexto_reporte[:500] if contexto_reporte else '',
                    "descripcion": descripcion_reporte[:500] if descripcion_reporte else ''
                }
            )
            
            # Preparar documentos para indexar
            documents = []
            metadatas = []
            ids = []
            
            # DOCUMENTO MAESTRO: Contexto completo del reporte (siempre se indexa primero)
            documento_maestro = f"""DOCUMENTACIÓN DEL REPORTE: {reporte['nombre']}
            
📋 CÓDIGO: {codigo_reporte}

📝 DESCRIPCIÓN:
{descripcion_reporte}

🎯 CONTEXTO Y PROPÓSITO:
{contexto_reporte}

📊 ESTRUCTURA DE CAMPOS:
"""
            for campo in campos_config:
                documento_maestro += f"\n• {campo.get('etiqueta', campo.get('nombre'))}"
                documento_maestro += f"\n  - Nombre técnico: {campo.get('nombre')}"
                documento_maestro += f"\n  - Tipo: {campo.get('tipo_dato', 'texto')}"
                if campo.get('descripcion'):
                    documento_maestro += f"\n  - Descripción: {campo.get('descripcion')}"
                if campo.get('ejemplo'):
                    documento_maestro += f"\n  - Ejemplo: {campo.get('ejemplo')}"
                documento_maestro += "\n"
            
            documents.append(documento_maestro)
            metadatas.append({
                'tipo': 'documentacion_reporte',
                'reporte': codigo_reporte,
                'es_maestro': True
            })
            ids.append(f"{codigo_reporte}_MAESTRO")
            
            # Agregar registros de datos
            for idx, registro in enumerate(datos):
                # Convertir datos a texto descriptivo con contexto
                datos_dict = registro['datos']
                
                # Encabezado con contexto del reporte
                texto = f"Reporte: {reporte['nombre']}\n"
                if contexto_reporte:
                    texto += f"Contexto: {contexto_reporte[:200]}\n"
                texto += "\n--- Registro ---\n"
                
                # Agregar cada campo con su descripción
                for k, v in datos_dict.items():
                    if v is not None:
                        # Usar documentación del campo si existe
                        if k in docs_campos and docs_campos[k].get('descripcion'):
                            texto += f"{docs_campos[k]['etiqueta']} ({docs_campos[k]['descripcion']}): {v}\n"
                        else:
                            texto += f"{k}: {v}\n"
                
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
            
            # Obtener contexto del reporte
            contexto_reporte = reporte.get('contexto', '')
            descripcion_reporte = reporte.get('descripcion', '')
            campos_config = reporte.get('campos', [])
            
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

📋 CONTEXTO DEL REPORTE:
{contexto_reporte if contexto_reporte else 'No especificado'}

📝 DESCRIPCIÓN:
{descripcion_reporte if descripcion_reporte else 'No especificada'}

📊 DATOS:
Total de registros: {resumen['total_registros']}
Columnas: {', '.join(resumen['columnas'])}

Estadísticas numéricas:
{json.dumps(numericas, indent=2)}

Muestra de datos:
{json.dumps(resumen['muestra_datos'], indent=2)}

Proporciona un análisis detallado que incluya:
1. Resumen ejecutivo (considerando el contexto del reporte)
2. Insights principales basados en el propósito del reporte
3. Tendencias identificadas
4. Recomendaciones específicas para este tipo de datos
5. Alertas o anomalías (si las hay)

Responde en español y de forma clara y profesional."""

            elif tipo_analisis == 'tendencias':
                prompt = f"""Analiza las tendencias en los datos del reporte "{reporte['nombre']}".

📋 CONTEXTO DEL REPORTE:
{contexto_reporte if contexto_reporte else 'No especificado'}
                
Datos disponibles: {resumen['total_registros']} registros
Columnas: {', '.join(resumen['columnas'])}

Identifica:
1. Tendencias temporales relevantes al contexto del reporte
2. Patrones recurrentes  
3. Proyecciones futuras basadas en el propósito del reporte
4. Cambios significativos que requieren atención

Datos de muestra:
{json.dumps(resumen['muestra_datos'], indent=2)}"""

            elif tipo_analisis == 'anomalias':
                prompt = f"""Detecta anomalías en los datos del reporte "{reporte['nombre']}".

📋 CONTEXTO DEL REPORTE:
{contexto_reporte if contexto_reporte else 'No especificado'}

Estadísticas:
{json.dumps(numericas, indent=2)}

Identifica valores atípicos, inconsistencias o datos sospechosos que no se ajusten al propósito del reporte.
Considera el contexto del reporte para determinar qué es anormal.

Muestra de datos: 
{json.dumps(resumen['muestra_datos'], indent=2)}"""
            
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
    
    def responder_pregunta(self, codigo_reporte: str, pregunta: str, session_id: str = "default"):
        """Responder pregunta sobre los datos usando RAG + LLM + Function Calling + Memoria"""
        if not self.openai_client:
            return {'error': 'OpenAI no configurado'}
        
        try:
            # Obtener info del reporte
            reporte = self.db_manager.obtener_reporte(codigo_reporte)
            
            # Obtener contexto y descripción del reporte
            contexto_reporte = reporte.get('contexto', 'No especificado')
            descripcion_reporte = reporte.get('descripcion', '')
            campos_config = reporte.get('campos', [])
            
            # Documentación de campos
            docs_campos_texto = "\n".join([
                f"  • {c.get('etiqueta', c.get('nombre'))}: {c.get('descripcion', 'Sin descripción')} (Tipo: {c.get('tipo_dato', c.get('tipo', 'texto'))})"
                for c in campos_config
            ])
            
            # Obtener lista de campos disponibles
            campos_disponibles = [c.get('nombre') for c in campos_config]
            
            # Preparar contexto del sistema con información del reporte
            system_context = f"""Eres un analista de datos experto con capacidad de ejecutar funciones para analizar datos.

🎯 REPORTE ACTUAL: {reporte['nombre']}
📋 CÓDIGO: {codigo_reporte}

CONTEXTO DEL NEGOCIO:
{contexto_reporte}

📊 CAMPOS DISPONIBLES:
{docs_campos_texto}

🔧 CAPACIDADES:
✅ Puedes ejecutar funciones para calcular totales, promedios, agrupaciones, comparaciones
✅ Puedes filtrar por fechas y criterios específicos
✅ Puedes hacer análisis comparativos entre períodos
✅ Tienes acceso completo a los datos del reporte

💡 INSTRUCCIONES:
- USA las funciones disponibles para obtener datos precisos
- Para cálculos, SIEMPRE usa calcular_total_campo
- Para rankings/tops, usa agrupar_por_campo  
- Para comparaciones temporales, usa comparar_periodos
- Responde en español con números específicos
- Presenta resultados de forma clara y profesional
- Si necesitas fechas y no las especifican, pregunta o asume el mes actual (febrero 2026)

CAMPOS NUMÉRICOS COMUNES: {', '.join([c.get('nombre') for c in campos_config if c.get('tipo_dato') in ['numero', 'decimal'] or c.get('tipo') in ['numero', 'decimal']])}
"""

            # Obtener historial de conversación
            historial = self.obtener_historial(session_id)
            
            # Construir mensajes para OpenAI
            messages = [{"role": "system", "content": system_context}]
            messages.extend(historial)  # Agregar historial previo
            messages.append({"role": "user", "content": pregunta})
            
            # Primera llamada con function calling
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self._get_available_functions(),
                tool_choice="auto",
                temperature=0.2
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # Si el modelo decidió usar funciones
            if tool_calls:
                # Agregar la respuesta del asistente al historial
                messages.append(response_message)
                
                # Ejecutar cada función solicitada
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🔧 Ejecutando función: {function_name} con args: {function_args}")
                    
                    # Ejecutar la función
                    function_response = self._ejecutar_funcion(function_name, function_args, codigo_reporte)
                    
                    # Agregar resultado de la función a los mensajes
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response, ensure_ascii=False)
                    })
                
                # Segunda llamada para obtener respuesta final con los resultados de las funciones  
                second_response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.2
                )
                
                respuesta_final = second_response.choices[0].message.content
                
                # Guardar en historial
                self.agregar_mensaje(session_id, "user", pregunta)
                self.agregar_mensaje(session_id, "assistant", respuesta_final)
                
                return {
                    'pregunta': pregunta,
                    'respuesta': respuesta_final,
                    'funciones_ejecutadas': [tc.function.name for tc in tool_calls],
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # No se usaron funciones, respuesta directa
                respuesta_final = response_message.content
                
                # Guardar en historial
                self.agregar_mensaje(session_id, "user", pregunta)
                self.agregar_mensaje(session_id, "assistant", respuesta_final)
                
                return {
                    'pregunta': pregunta,
                    'respuesta': respuesta_final,
                    'funciones_ejecutadas': [],
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error respondiendo pregunta: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'error': str(e), 'traceback': traceback.format_exc()}
            
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
