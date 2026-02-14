"""
Script de prueba para el sistema de control de periodos
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000"

def test_crear_reporte_con_validacion():
    """Prueba crear un reporte con validación de IA"""
    print("\n=== PRUEBA 1: Crear reporte con validación ===")
    
    data = {
        "nombre": "Ventas Diarias",
        "descripcion": "Reporte de ventas del día",
        "requiere_periodo": True,
        "tipo_periodo": "diario",
        "campos": [
            {"nombre": "fecha", "tipo": "date", "descripcion": "Fecha de la venta"},
            {"nombre": "producto", "tipo": "text", "descripcion": "Nombre del producto"},
            {"nombre": "cantidad", "tipo": "number", "descripcion": "Cantidad vendida"},
            {"nombre": "precio_unitario", "tipo": "number", "descripcion": "Precio por unidad"},
            {"nombre": "total", "tipo": "number", "descripcion": "Total de la venta"}
        ],
        "datos_muestra": [
            {
                "fecha": "2024-01-15",
                "producto": "Laptop",
                "cantidad": 2,
                "precio_unitario": 1200.00,
                "total": 2400.00
            },
            {
                "fecha": "2024-01-15",
                "producto": "Mouse",
                "cantidad": 5,
                "precio_unitario": 25.00,
                "total": 125.00
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/reportes/crear-con-validacion", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


def test_cargar_datos_reporte(codigo):
    """Prueba cargar datos a un reporte"""
    print(f"\n=== PRUEBA 2: Cargar datos al reporte {codigo} ===")
    
    # Datos para hoy
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    
    data = {
        "datos": [
            {
                "fecha": fecha_hoy,
                "producto": "Laptop Dell",
                "cantidad": 3,
                "precio_unitario": 1500.00,
                "total": 4500.00
            },
            {
                "fecha": fecha_hoy,
                "producto": "Teclado Mecánico",
                "cantidad": 8,
                "precio_unitario": 120.00,
                "total": 960.00
            },
            {
                "fecha": fecha_hoy,
                "producto": "Monitor 27 pulgadas",
                "cantidad": 4,
                "precio_unitario": 350.00,
                "total": 1400.00
            }
        ],
        "archivo_nombre": "ventas_test.json"
    }
    
    response = requests.post(f"{BASE_URL}/api/reportes/{codigo}/cargar-datos", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


def test_obtener_carga(carga_id):
    """Prueba obtener detalles de una carga"""
    print(f"\n=== PRUEBA 3: Obtener detalles de carga {carga_id} ===")
    
    response = requests.get(f"{BASE_URL}/api/cargas/{carga_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


def test_aprobar_carga(carga_id):
    """Prueba aprobar una carga"""
    print(f"\n=== PRUEBA 4: Aprobar carga {carga_id} ===")
    
    data = {
        "usuario": "admin",
        "notas": "Prueba de aprobación automática"
    }
    
    response = requests.post(f"{BASE_URL}/api/cargas/{carga_id}/aprobar", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


def test_listar_cargas(codigo):
    """Prueba listar historial de cargas"""
    print(f"\n=== PRUEBA 5: Listar cargas del reporte {codigo} ===")
    
    response = requests.get(f"{BASE_URL}/api/reportes/{codigo}/cargas")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


def test_consultar_datos_periodo(codigo):
    """Prueba consultar datos por periodo"""
    print(f"\n=== PRUEBA 6: Consultar datos por periodo ===")
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    
    response = requests.get(f"{BASE_URL}/api/reportes/{codigo}/datos-por-periodo?fecha={fecha_hoy}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


def test_cargar_periodo_duplicado(codigo):
    """Prueba intentar cargar el mismo periodo dos veces (debe fallar)"""
    print(f"\n=== PRUEBA 7: Intentar cargar periodo duplicado ===")
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    
    data = {
        "datos": [
            {
                "fecha": fecha_hoy,
                "producto": "Test Duplicado",
                "cantidad": 1,
                "precio_unitario": 100.00,
                "total": 100.00
            },
            {
                "fecha": fecha_hoy,
                "producto": "Test Duplicado 2",
                "cantidad": 2,
                "precio_unitario": 50.00,
                "total": 100.00
            }
        ],
        "archivo_nombre": "intento_duplicado.json"
    }
    
    response = requests.post(f"{BASE_URL}/api/reportes/{codigo}/cargar-datos", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


if __name__ == '__main__':
    print("=" * 70)
    print("PRUEBA COMPLETA DEL SISTEMA DE CONTROL DE PERIODOS")
    print("=" * 70)
    
    try:
        # 1. Crear reporte con validación
        resultado = test_crear_reporte_con_validacion()
        
        if not resultado.get('success'):
            print("\n❌ Error: No se pudo crear el reporte")
            print("Razón:", resultado.get('mensaje'))
            exit(1)
        
        codigo_reporte = resultado['reporte']['codigo']
        print(f"\n✓ Reporte creado: {codigo_reporte}")
        
        # 2. Cargar datos
        resultado_carga = test_cargar_datos_reporte(codigo_reporte)
        
        if not resultado_carga.get('success'):
            print("\n❌ Error: No se pudieron cargar los datos")
            exit(1)
        
        carga_id = resultado_carga['carga_id']
        print(f"\n✓ Carga creada: {carga_id}")
        
        # 3. Obtener detalles de carga
        test_obtener_carga(carga_id)
        
        # 4. Aprobar carga
        test_aprobar_carga(carga_id)
        print(f"\n✓ Carga aprobada")
        
        # 5. Listar historial
        test_listar_cargas(codigo_reporte)
        
        # 6. Consultar datos por periodo
        test_consultar_datos_periodo(codigo_reporte)
        
        # 7. Intentar cargar periodo duplicado (debe fallar)
        test_cargar_periodo_duplicado(codigo_reporte)
        
        print("\n" + "=" * 70)
        print("✓ TODAS LAS PRUEBAS COMPLETADAS")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error en pruebas: {e}")
        import traceback
        traceback.print_exc()
