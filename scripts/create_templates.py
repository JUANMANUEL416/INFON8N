"""
Script para generar plantillas Excel vacías con estructura fija
Ejecutar: python create_templates.py
"""

import pandas as pd
from datetime import datetime
import os

# Definición de modelos/plantillas
TEMPLATES = {
    'facturacion_diaria': {
        'filename': 'plantilla_facturacion_diaria.xlsx',
        'columns': ['numero_factura', 'fecha', 'cliente', 'monto', 'estado'],
        'description': 'Facturación diaria - campos obligatorios',
        'sample_row': {
            'numero_factura': 'FAC-2024-0001',
            'fecha': datetime.now().date(),
            'cliente': 'Nombre del Cliente',
            'monto': 1000.00,
            'estado': 'pendiente'
        },
        'validations': {
            'numero_factura': 'Texto único (ej: FAC-2024-0001)',
            'fecha': 'Fecha (YYYY-MM-DD)',
            'cliente': 'Texto (nombre del cliente)',
            'monto': 'Número decimal (ej: 1500.50)',
            'estado': 'pendiente|pagada|vencida'
        }
    },
    
    'cartera_vencida': {
        'filename': 'plantilla_cartera_vencida.xlsx',
        'columns': ['numero_factura', 'cliente', 'monto_adeudado', 'dias_vencido', 'estado'],
        'description': 'Cartera vencida - seguimiento de cuentas por cobrar',
        'sample_row': {
            'numero_factura': 'FAC-2024-0001',
            'cliente': 'Nombre del Cliente',
            'monto_adeudado': 2500.00,
            'dias_vencido': 15,
            'estado': 'vigente'
        },
        'validations': {
            'numero_factura': 'Texto (ej: FAC-2024-0001) - opcional',
            'cliente': 'Texto (nombre del cliente)',
            'monto_adeudado': 'Número decimal',
            'dias_vencido': 'Número entero (días)',
            'estado': 'vigente|vencida|proxima_vencer'
        }
    },
    
    'ventas_productos': {
        'filename': 'plantilla_ventas_productos.xlsx',
        'columns': ['id_producto', 'nombre', 'cantidad_vendida', 'precio_unitario', 'fecha'],
        'description': 'Ventas por producto',
        'sample_row': {
            'id_producto': 'PROD-1001',
            'nombre': 'Nombre del Producto',
            'cantidad_vendida': 10,
            'precio_unitario': 150.00,
            'fecha': datetime.now().date()
        },
        'validations': {
            'id_producto': 'Texto único (ej: PROD-1001)',
            'nombre': 'Texto (nombre del producto)',
            'cantidad_vendida': 'Número entero',
            'precio_unitario': 'Número decimal',
            'fecha': 'Fecha (YYYY-MM-DD)'
        }
    },
    
    'gastos_operativos': {
        'filename': 'plantilla_gastos_operativos.xlsx',
        'columns': ['fecha', 'categoria', 'descripcion', 'monto', 'area'],
        'description': 'Gastos operativos diarios',
        'sample_row': {
            'fecha': datetime.now().date(),
            'categoria': 'Servicios',
            'descripcion': 'Descripción del gasto',
            'monto': 500.00,
            'area': 'Administración'
        },
        'validations': {
            'fecha': 'Fecha (YYYY-MM-DD)',
            'categoria': 'Servicios|Materiales|Personal|Otros',
            'descripcion': 'Texto descriptivo',
            'monto': 'Número decimal',
            'area': 'Texto (departamento/área)'
        }
    }
}

def create_template(template_name, config):
    """Crear una plantilla Excel vacía"""
    
    # Crear DataFrame con columnas
    df_empty = pd.DataFrame(columns=config['columns'])
    
    # Crear DataFrame con ejemplo
    df_sample = pd.DataFrame([config['sample_row']])
    
    # Crear hoja de validaciones
    validations_data = [
        {'Campo': col, 'Descripción': config['validations'].get(col, '')}
        for col in config['columns']
    ]
    df_validations = pd.DataFrame(validations_data)
    
    # Guardar en Excel con múltiples hojas
    filepath = f'../data/plantillas/{config["filename"]}'
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Hoja 1: Datos (vacía)
        df_empty.to_excel(writer, sheet_name='Datos', index=False)
        
        # Hoja 2: Ejemplo
        df_sample.to_excel(writer, sheet_name='Ejemplo', index=False)
        
        # Hoja 3: Validaciones
        df_validations.to_excel(writer, sheet_name='Validaciones', index=False)
    
    print(f"✓ {config['filename']}")
    print(f"  Columnas: {', '.join(config['columns'])}")
    print(f"  Descripción: {config['description']}\n")

def create_readme():
    """Crear README con documentación de plantillas"""
    
    readme_content = """# 📋 Plantillas de Datos - Sistema de Informes

## ¿Qué son las plantillas?

Las plantillas son archivos Excel con estructura fija que garantizan que los datos se carguen correctamente al sistema.

## 📁 Plantillas Disponibles

"""
    
    for template_name, config in TEMPLATES.items():
        readme_content += f"### {config['filename']}\n\n"
        readme_content += f"**Descripción:** {config['description']}\n\n"
        readme_content += "**Columnas obligatorias:**\n\n"
        readme_content += "| Campo | Descripción |\n"
        readme_content += "|-------|-------------|\n"
        
        for col in config['columns']:
            desc = config['validations'].get(col, '')
            readme_content += f"| `{col}` | {desc} |\n"
        
        readme_content += f"\n**Archivo:** `{config['filename']}`\n\n"
        readme_content += "---\n\n"
    
    readme_content += """## 🚀 Cómo usar las plantillas

1. **Descargar la plantilla** que necesites de la carpeta `data/plantillas/`
2. **Abrir con Excel** y revisar:
   - Hoja "Datos": Aquí ingresas tus datos
   - Hoja "Ejemplo": Fila de ejemplo con formato correcto
   - Hoja "Validaciones": Descripción de cada campo
3. **Llenar solo la hoja "Datos"** con tu información
4. **Guardar y subir** al sistema vía n8n o API

## ⚠️ Importante

- **NO cambies los nombres de las columnas**
- **Respeta los tipos de datos** (fechas, números, texto)
- **No agregues columnas extra** en la hoja "Datos"
- **No borres las hojas** "Ejemplo" y "Validaciones"

## 📤 Subir datos

### Opción 1: Via n8n
```
http://localhost:5678
Usar workflow: "workflow-webhook-upload"
```

### Opción 2: Via API directa
```bash
curl -X POST http://localhost:5000/upload \\
  -F "file=@plantilla_facturacion_diaria.xlsx" \\
  -F "type=facturas"
```

## 🔍 Tipos de datos soportados

| Tipo en API | Plantilla recomendada |
|-------------|-----------------------|
| `facturas` | plantilla_facturacion_diaria.xlsx |
| `cartera` | plantilla_cartera_vencida.xlsx |
| `productos` | plantilla_ventas_productos.xlsx |
| `gastos` | plantilla_gastos_operativos.xlsx |
"""
    
    with open('../data/plantillas/README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✓ README.md creado con documentación completa\n")

if __name__ == '__main__':
    print("📝 Generando plantillas Excel...\n")
    
    # Crear carpeta si no existe
    os.makedirs('../data/plantillas', exist_ok=True)
    
    # Generar cada plantilla
    for template_name, config in TEMPLATES.items():
        create_template(template_name, config)
    
    # Crear README
    create_readme()
    
    print("✅ Todas las plantillas generadas en data/plantillas/")
    print("\n💡 Consulta data/plantillas/README.md para ver la documentación")
