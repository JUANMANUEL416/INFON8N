"""
Script para generar archivos Excel de prueba
Ejecutar: python generate_sample_data.py
"""

import pandas as pd
from datetime import datetime, timedelta
import random

def generar_facturas(cantidad=50):
    """Generar datos de facturas de ejemplo"""
    datos = []
    clientes = ['Empresa A', 'Empresa B', 'Empresa C', 'Empresa D', 'Empresa E', 'Tienda 1', 'Tienda 2']
    
    for i in range(cantidad):
        fecha = datetime.now() - timedelta(days=random.randint(1, 90))
        datos.append({
            'numero_factura': f'FAC-2024-{i+1000}',
            'fecha': fecha.date(),
            'cliente': random.choice(clientes),
            'monto': round(random.uniform(100, 5000), 2),
            'estado': random.choice(['pagada', 'pendiente', 'vencida'])
        })
    
    df = pd.DataFrame(datos)
    df.to_excel('../data/facturas_ejemplo.xlsx', index=False)
    print(f"✓ Creado: data/facturas_ejemplo.xlsx ({cantidad} registros)")

def generar_cartera(cantidad=30):
    """Generar datos de cartera vencida"""
    datos = []
    clientes = ['Empresa A', 'Empresa B', 'Empresa C', 'Empresa D', 'Empresa E', 'Tienda 1', 'Tienda 2']
    
    for i in range(cantidad):
        dias_vencido = random.randint(5, 120)
        datos.append({
            'numero_factura': f'FAC-2024-{random.randint(1000, 1050)}',
            'cliente': random.choice(clientes),
            'monto_adeudado': round(random.uniform(500, 3000), 2),
            'dias_vencido': dias_vencido,
            'estado': 'vencida' if dias_vencido > 30 else 'proxima_vencer'
        })
    
    df = pd.DataFrame(datos)
    df.to_excel('../data/cartera_ejemplo.xlsx', index=False)
    print(f"✓ Creado: data/cartera_ejemplo.xlsx ({cantidad} registros)")

def generar_productos(cantidad=20):
    """Generar datos de productos/ventas"""
    datos = []
    productos = ['Producto A', 'Producto B', 'Producto C', 'Producto D', 'Producto E']
    
    for i in range(cantidad):
        datos.append({
            'id_producto': f'PROD-{i+1000}',
            'nombre': random.choice(productos),
            'cantidad_vendida': random.randint(1, 100),
            'precio_unitario': round(random.uniform(10, 500), 2),
            'fecha': (datetime.now() - timedelta(days=random.randint(1, 30))).date()
        })
    
    df = pd.DataFrame(datos)
    df.to_excel('../data/productos_ejemplo.xlsx', index=False)
    print(f"✓ Creado: data/productos_ejemplo.xlsx ({cantidad} registros)")

if __name__ == '__main__':
    print("📊 Generando datos de ejemplo...\n")
    generar_facturas(50)
    generar_cartera(30)
    generar_productos(20)
    print("\n✅ Datos generados en carpeta 'data/'")
    print("\n💡 Tip: Sube estos archivos a http://localhost:5000/upload")
