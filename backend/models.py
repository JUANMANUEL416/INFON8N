"""
Modelos de base de datos para sistema dinámico de reportes
"""
from datetime import datetime
from typing import Dict, List, Optional
import json

class ReporteConfig:
    """Configuración de un reporte dinámico"""
    
    def __init__(self, data: dict):
        self.id = data.get('id')
        self.nombre = data.get('nombre')
        self.codigo = data.get('codigo')  # Identificador único (ej: facturas_diarias)
        self.descripcion = data.get('descripcion')
        self.contexto = data.get('contexto')  # Contexto para IA/análisis
        self.categoria = data.get('categoria')
        self.icono = data.get('icono', '📊')
        self.activo = data.get('activo', True)
        self.campos = data.get('campos', [])  # Lista de campos/columnas
        self.relaciones = data.get('relaciones', [])  # Relaciones con otros reportes
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'codigo': self.codigo,
            'descripcion': self.descripcion,
            'contexto': self.contexto,
            'categoria': self.categoria,
            'icono': self.icono,
            'activo': self.activo,
            'campos': self.campos,
            'relaciones': self.relaciones,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class CampoConfig:
    """Configuración de un campo/columna"""
    
    TIPOS_DATOS = ['texto', 'numero', 'decimal', 'fecha', 'booleano', 'email', 'telefono']
    
    def __init__(self, data: dict):
        self.nombre = data.get('nombre')  # Nombre técnico (sin espacios)
        self.etiqueta = data.get('etiqueta')  # Nombre visible
        self.tipo_dato = data.get('tipo_dato', 'texto')
        self.obligatorio = data.get('obligatorio', False)
        self.descripcion = data.get('descripcion')
        self.valores_permitidos = data.get('valores_permitidos', [])  # Para select/enum
        self.validacion_regex = data.get('validacion_regex')
        self.valor_default = data.get('valor_default')
        self.orden = data.get('orden', 0)
        self.ejemplo = data.get('ejemplo')
        
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'etiqueta': self.etiqueta,
            'tipo_dato': self.tipo_dato,
            'obligatorio': self.obligatorio,
            'descripcion': self.descripcion,
            'valores_permitidos': self.valores_permitidos,
            'validacion_regex': self.validacion_regex,
            'valor_default': self.valor_default,
            'orden': self.orden,
            'ejemplo': self.ejemplo
        }
    
    def get_sql_type(self):
        """Convertir tipo de dato a SQL"""
        mapping = {
            'texto': 'VARCHAR(500)',
            'numero': 'INTEGER',
            'decimal': 'DECIMAL(15,2)',
            'fecha': 'DATE',
            'booleano': 'BOOLEAN',
            'email': 'VARCHAR(255)',
            'telefono': 'VARCHAR(20)'
        }
        return mapping.get(self.tipo_dato, 'TEXT')

class RelacionConfig:
    """Configuración de relación entre reportes"""
    
    def __init__(self, data: dict):
        self.reporte_destino = data.get('reporte_destino')  # Código del reporte relacionado
        self.campo_origen = data.get('campo_origen')  # Campo en este reporte
        self.campo_destino = data.get('campo_destino')  # Campo en el reporte destino
        self.tipo = data.get('tipo', 'referencia')  # referencia, agregacion, etc
        self.descripcion = data.get('descripcion')
    
    def to_dict(self):
        return {
            'reporte_destino': self.reporte_destino,
            'campo_origen': self.campo_origen,
            'campo_destino': self.campo_destino,
            'tipo': self.tipo,
            'descripcion': self.descripcion
        }
