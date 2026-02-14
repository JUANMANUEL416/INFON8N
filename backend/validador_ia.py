"""
Validador IA para estructura y contenido de reportes
Valida campos, duplicados, comprensión de datos
"""
import os
import json
from typing import Dict, List, Tuple, Any
from openai import OpenAI

class ValidadorIA:
    """
    Valida reportes usando GPT-4o para:
    1. Comprender estructura de campos
    2. Detectar duplicados
    3. Validar que tiene campo de fecha/periodo
    4. Identificar campos que requieren aclaración
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-4o"
    
    def validar_estructura_reporte(
        self, 
        nombre_reporte: str,
        campos: List[Dict[str, Any]],
        datos_muestra: List[Dict] = None,
        descripcion: str = None
    ) -> Dict[str, Any]:
        """
        Valida la estructura de un nuevo reporte
        
        Args:
            nombre_reporte: Nombre del reporte
            campos: Lista de campos con {nombre, tipo, descripcion}
            datos_muestra: Datos de ejemplo (primeras filas si viene de Excel)
            descripcion: Descripción del reporte proporcionada por usuario
            
        Returns:
            {
                "valido": bool,
                "comprensible": bool,
                "tiene_campo_fecha": bool,
                "campo_fecha_sugerido": str,
                "campos_claros": list,
                "campos_requieren_aclaracion": list,
                "duplicados_detectados": list,
                "sugerencias": list,
                "mensaje": str
            }
        """
        
        # Preparar información para IA
        info_campos = []
        for campo in campos:
            info_campos.append({
                "nombre": campo.get('nombre', campo.get('name', '')),
                "tipo": campo.get('tipo', campo.get('type', 'text')),
                "descripcion": campo.get('descripcion', campo.get('description', ''))
            })
        
        prompt = f"""Eres un experto en análisis de datos y estructuras de reportes.

Analiza la siguiente estructura de reporte y valida:

NOMBRE DEL REPORTE: {nombre_reporte}
DESCRIPCIÓN: {descripcion or 'No proporcionada'}

CAMPOS:
{json.dumps(info_campos, indent=2, ensure_ascii=False)}
"""

        if datos_muestra:
            prompt += f"""

DATOS DE MUESTRA (primeras {len(datos_muestra)} filas):
{json.dumps(datos_muestra[:5], indent=2, ensure_ascii=False)}
"""

        prompt += """

VALIDACIONES REQUERIDAS:

1. **Campo de Fecha/Periodo**: ¿El reporte tiene algún campo que represente fecha o periodo?
   - Identificar cuál es
   - Si no tiene, es CRÍTICO mencionarlo

2. **Comprensibilidad**: ¿Los campos son claros y comprensibles?
   - Listar campos que están claros
   - Listar campos que requieren aclaración del usuario

3. **Duplicados**: ¿Hay campos duplicados o muy similares que puedan causar confusión?

4. **Tipo de datos**: ¿Los tipos de datos son apropiados?

5. **Sugerencias**: Mejoras para la estructura

Responde ÚNICAMENTE en formato JSON válido con esta estructura exacta:
{
    "valido": true/false,
    "comprensible": true/false,
    "tiene_campo_fecha": true/false,
    "campo_fecha_sugerido": "nombre_del_campo o null",
    "tipo_periodo_sugerido": "diario/semanal/mensual/etc o null",
    "campos_claros": ["campo1", "campo2"],
    "campos_requieren_aclaracion": [
        {"campo": "nombre", "razon": "no está claro qué representa"},
        ...
    ],
    "duplicados_detectados": [
        {"campos": ["campo1", "campo2"], "razon": "parecen representar lo mismo"}
    ],
    "problemas_tipos": [
        {"campo": "nombre", "tipo_actual": "text", "tipo_sugerido": "number", "razon": "..."}
    ],
    "sugerencias": ["sugerencia 1", "sugerencia 2"],
    "mensaje": "Resumen de la validación en 2-3 oraciones"
}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Eres un experto validador de estructuras de datos. Respondes ÚNICAMENTE con JSON válido."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            resultado = json.loads(response.choices[0].message.content)
            
            # Asegurar que tiene todos los campos
            resultado.setdefault('valido', True)
            resultado.setdefault('comprensible', True)
            resultado.setdefault('tiene_campo_fecha', False)
            resultado.setdefault('campo_fecha_sugerido', None)
            resultado.setdefault('tipo_periodo_sugerido', None)
            resultado.setdefault('campos_claros', [])
            resultado.setdefault('campos_requieren_aclaracion', [])
            resultado.setdefault('duplicados_detectados', [])
            resultado.setdefault('problemas_tipos', [])
            resultado.setdefault('sugerencias', [])
            resultado.setdefault('mensaje', 'Validación completada')
            
            # Determinar si es válido para continuar
            tiene_problemas_criticos = (
                not resultado['tiene_campo_fecha'] or
                len(resultado['campos_requieren_aclaracion']) > len(campos) * 0.5 or
                len(resultado['duplicados_detectados']) > 0
            )
            
            resultado['valido'] = not tiene_problemas_criticos
            
            return resultado
            
        except Exception as e:
            return {
                "valido": False,
                "comprensible": False,
                "tiene_campo_fecha": False,
                "campo_fecha_sugerido": None,
                "tipo_periodo_sugerido": None,
                "campos_claros": [],
                "campos_requieren_aclaracion": [{"campo": "general", "razon": f"Error en validación: {str(e)}"}],
                "duplicados_detectados": [],
                "problemas_tipos": [],
                "sugerencias": [],
                "mensaje": f"Error al validar con IA: {str(e)}"
            }
    
    def validar_datos_carga(
        self,
        reporte_codigo: str,
        reporte_nombre: str,
        campos_esperados: List[Dict],
        datos: List[Dict],
        periodo_esperado: Dict = None
    ) -> Dict[str, Any]:
        """
        Valida una carga de datos contra la estructura esperada
        
        Args:
            reporte_codigo: Código del reporte
            reporte_nombre: Nombre del reporte
            campos_esperados: Campos definidos en reportes_config
            datos: Datos a validar
            periodo_esperado: {tipo, inicio, fin} si aplica
            
        Returns:
            {
                "valido": bool,
                "cantidad_registros": int,
                "registros_validos": int,
                "registros_invalidos": int,
                "errores": [
                    {
                        "fila": int,
                        "campo": str,
                        "valor": any,
                        "error": str
                    }
                ],
                "campos_faltantes": list,
                "campos_extra": list,
                "fuera_de_periodo": list,
                "mensaje": str
            }
        """
        
        if not datos or len(datos) < 2:
            return {
                "valido": False,
                "cantidad_registros": len(datos) if datos else 0,
                "registros_validos": 0,
                "registros_invalidos": 0,
                "errores": [{"fila": 0, "campo": "general", "valor": None, "error": "Mínimo 2 registros requeridos"}],
                "campos_faltantes": [],
                "campos_extra": [],
                "fuera_de_periodo": [],
                "mensaje": "Se requieren al menos 2 registros de datos"
            }
        
        # Validar estructura de campos
        campos_esperados_nombres = {c.get('nombre', c.get('name', '')) for c in campos_esperados}
        campos_datos = set(datos[0].keys()) if datos else set()
        
        campos_faltantes = list(campos_esperados_nombres - campos_datos)
        campos_extra = list(campos_datos - campos_esperados_nombres)
        
        errores = []
        registros_validos = 0
        registros_invalidos = 0
        fuera_de_periodo = []
        
        # Validar cada registro
        for idx, registro in enumerate(datos, start=1):
            errores_fila = []
            
            # Verificar campos faltantes en este registro
            for campo in campos_faltantes:
                errores_fila.append({
                    "fila": idx,
                    "campo": campo,
                    "valor": None,
                    "error": f"Campo '{campo}' faltante"
                })
            
            # Validar periodo si aplica
            if periodo_esperado and periodo_esperado.get('campo_fecha'):
                campo_fecha = periodo_esperado['campo_fecha']
                valor_fecha = registro.get(campo_fecha)
                
                if valor_fecha:
                    try:
                        from datetime import datetime
                        fecha = datetime.strptime(str(valor_fecha), '%Y-%m-%d').date() if isinstance(valor_fecha, str) else valor_fecha
                        
                        if periodo_esperado.get('inicio') and periodo_esperado.get('fin'):
                            inicio = periodo_esperado['inicio']
                            fin = periodo_esperado['fin']
                            
                            if not (inicio <= fecha <= fin):
                                fuera_de_periodo.append({
                                    "fila": idx,
                                    "fecha": str(fecha),
                                    "periodo_esperado": f"{inicio} - {fin}"
                                })
                                errores_fila.append({
                                    "fila": idx,
                                    "campo": campo_fecha,
                                    "valor": str(fecha),
                                    "error": f"Fecha fuera del periodo esperado ({inicio} - {fin})"
                                })
                    except Exception as e:
                        errores_fila.append({
                            "fila": idx,
                            "campo": campo_fecha,
                            "valor": valor_fecha,
                            "error": f"Formato de fecha inválido: {str(e)}"
                        })
            
            if errores_fila:
                errores.extend(errores_fila)
                registros_invalidos += 1
            else:
                registros_validos += 1
        
        # Determinar si es válido
        valido = (
            len(campos_faltantes) == 0 and
            registros_validos >= 2 and
            registros_invalidos == 0
        )
        
        mensaje = f"Validación completada: {registros_validos} válidos, {registros_invalidos} inválidos"
        if campos_faltantes:
            mensaje += f". Campos faltantes: {', '.join(campos_faltantes)}"
        if fuera_de_periodo:
            mensaje += f". {len(fuera_de_periodo)} registros fuera del periodo"
        
        return {
            "valido": valido,
            "cantidad_registros": len(datos),
            "registros_validos": registros_validos,
            "registros_invalidos": registros_invalidos,
            "errores": errores,
            "campos_faltantes": campos_faltantes,
            "campos_extra": campos_extra,
            "fuera_de_periodo": fuera_de_periodo,
            "mensaje": mensaje
        }
    
    def sugerir_aclaraciones(
        self,
        campo: str,
        contexto_reporte: str,
        datos_muestra: List[Any] = None
    ) -> str:
        """
        Sugiere qué aclaración hacer para un campo poco claro
        
        Args:
            campo: Nombre del campo
            contexto_reporte: Nombre/descripción del reporte
            datos_muestra: Valores de ejemplo del campo
            
        Returns:
            str: Pregunta sugerida para aclaración
        """
        
        prompt = f"""Necesitas aclaración sobre un campo en un reporte.

REPORTE: {contexto_reporte}
CAMPO: {campo}
"""
        if datos_muestra:
            prompt += f"VALORES DE EJEMPLO: {json.dumps(datos_muestra[:5], ensure_ascii=False)}\n"
        
        prompt += """
Genera una pregunta clara y específica para que el usuario aclare qué representa este campo.
La pregunta debe ser directa, en español, y ayudar a comprender el propósito del campo.

Responde ÚNICAMENTE con la pregunta, sin explicaciones adicionales.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Generas preguntas claras para aclarar campos de datos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"¿Qué representa el campo '{campo}' en este reporte?"


# Instancia global
validador_ia = ValidadorIA()
