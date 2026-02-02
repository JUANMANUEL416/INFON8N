"""
Script de migración e inicialización del nuevo sistema dinámico
Ejecutar: python migrate_to_dynamic.py
"""

import sys
sys.path.append('/app')

from db_manager import DatabaseManager
from models import ReporteConfig
import json

# Configuración de BD
DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'user': 'admin',
    'password': 'admin123',
    'database': 'informes_db'
}

def crear_reportes_ejemplo():
    """Crear reportes de ejemplo basados en el sistema anterior"""
    
    db = DatabaseManager(DB_CONFIG)
    
    reportes_ejemplo = [
        {
            'nombre': 'Facturación Diaria',
            'codigo': 'facturacion_diaria',
            'descripcion': 'Registro diario de facturas emitidas',
            'contexto': 'Este reporte contiene todas las facturas emitidas. Se usa para seguimiento de ventas y flujo de caja. Los montos están en pesos colombianos. El campo numero_factura debe ser único. El estado puede ser: pendiente, pagada o vencida.',
            'categoria': 'finanzas',
            'icono': '📊',
            'campos': [
                {
                    'nombre': 'numero_factura',
                    'etiqueta': 'Número de Factura',
                    'tipo_dato': 'texto',
                    'obligatorio': True,
                    'descripcion': 'Identificador único de la factura',
                    'ejemplo': 'FAC-2024-0001',
                    'orden': 0
                },
                {
                    'nombre': 'fecha',
                    'etiqueta': 'Fecha',
                    'tipo_dato': 'fecha',
                    'obligatorio': True,
                    'descripcion': 'Fecha de emisión de la factura',
                    'ejemplo': '2024-02-01',
                    'orden': 1
                },
                {
                    'nombre': 'cliente',
                    'etiqueta': 'Cliente',
                    'tipo_dato': 'texto',
                    'obligatorio': True,
                    'descripcion': 'Nombre del cliente',
                    'ejemplo': 'Empresa ABC Ltda',
                    'orden': 2
                },
                {
                    'nombre': 'monto',
                    'etiqueta': 'Monto',
                    'tipo_dato': 'decimal',
                    'obligatorio': True,
                    'descripcion': 'Valor total de la factura',
                    'ejemplo': '1500000.00',
                    'orden': 3
                },
                {
                    'nombre': 'estado',
                    'etiqueta': 'Estado',
                    'tipo_dato': 'texto',
                    'obligatorio': False,
                    'descripcion': 'Estado actual de la factura',
                    'valores_permitidos': ['pendiente', 'pagada', 'vencida'],
                    'ejemplo': 'pendiente',
                    'orden': 4
                }
            ],
            'relaciones': [
                {
                    'reporte_destino': 'cartera_vencida',
                    'campo_origen': 'numero_factura',
                    'campo_destino': 'numero_factura',
                    'descripcion': 'Las facturas pueden aparecer en cartera si no se pagan'
                }
            ]
        },
        {
            'nombre': 'Cartera Vencida',
            'codigo': 'cartera_vencida',
            'descripcion': 'Seguimiento de cuentas por cobrar',
            'contexto': 'Reporte de cartera morosa. Muestra facturas no pagadas y días de vencimiento. Los días_vencido indican cuántos días han pasado desde la fecha de vencimiento. Se relaciona con facturas mediante numero_factura.',
            'categoria': 'finanzas',
            'icono': '💰',
            'campos': [
                {
                    'nombre': 'numero_factura',
                    'etiqueta': 'Número de Factura',
                    'tipo_dato': 'texto',
                    'obligatorio': False,
                    'descripcion': 'Referencia a la factura original',
                    'ejemplo': 'FAC-2024-0001',
                    'orden': 0
                },
                {
                    'nombre': 'cliente',
                    'etiqueta': 'Cliente',
                    'tipo_dato': 'texto',
                    'obligatorio': True,
                    'descripcion': 'Nombre del cliente moroso',
                    'ejemplo': 'Empresa ABC Ltda',
                    'orden': 1
                },
                {
                    'nombre': 'monto_adeudado',
                    'etiqueta': 'Monto Adeudado',
                    'tipo_dato': 'decimal',
                    'obligatorio': True,
                    'descripcion': 'Valor pendiente de pago',
                    'ejemplo': '2500000.00',
                    'orden': 2
                },
                {
                    'nombre': 'dias_vencido',
                    'etiqueta': 'Días Vencido',
                    'tipo_dato': 'numero',
                    'obligatorio': False,
                    'descripcion': 'Días transcurridos desde vencimiento',
                    'ejemplo': '15',
                    'orden': 3
                },
                {
                    'nombre': 'estado',
                    'etiqueta': 'Estado',
                    'tipo_dato': 'texto',
                    'obligatorio': False,
                    'descripcion': 'Estado de la deuda',
                    'valores_permitidos': ['vigente', 'vencida', 'proxima_vencer'],
                    'ejemplo': 'vencida',
                    'orden': 4
                }
            ],
            'relaciones': [
                {
                    'reporte_destino': 'facturacion_diaria',
                    'campo_origen': 'numero_factura',
                    'campo_destino': 'numero_factura',
                    'descripcion': 'Referencia a la factura original'
                }
            ]
        }
    ]
    
    print("🚀 Iniciando migración a sistema dinámico...\n")
    
    # Inicializar tablas de metadatos
    print("📊 Creando tablas de metadatos...")
    if db.init_metadata_tables():
        print("✅ Tablas creadas correctamente\n")
    else:
        print("❌ Error creando tablas\n")
        return False
    
    # Crear reportes de ejemplo
    print("📝 Creando reportes de ejemplo...\n")
    
    for reporte_data in reportes_ejemplo:
        try:
            reporte = ReporteConfig(reporte_data)
            reporte_id = db.crear_reporte(reporte)
            print(f"  ✅ {reporte_data['nombre']} (ID: {reporte_id})")
        except Exception as e:
            print(f"  ❌ Error en {reporte_data['nombre']}: {e}")
    
    print("\n✨ Migración completada!")
    print("\n📖 Próximos pasos:")
    print("  1. Ir a http://localhost:5000/admin para ver el panel")
    print("  2. Crear nuevos reportes personalizados")
    print("  3. Los usuarios pueden acceder en http://localhost:5000")
    
    return True

if __name__ == '__main__':
    crear_reportes_ejemplo()
