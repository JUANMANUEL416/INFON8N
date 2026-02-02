"""
Script de prueba para cargar plantillas al sistema
Ejecutar: python test_upload.py
"""

import requests
import os
from pathlib import Path

BASE_URL = "http://localhost:5000"
PLANTILLAS_DIR = Path("../data/plantillas")

def test_health():
    """Verificar que el backend esté funcionando"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✓ Backend funcionando correctamente")
            return True
        else:
            print("✗ Backend no responde correctamente")
            return False
    except Exception as e:
        print(f"✗ Error conectando al backend: {e}")
        print("  Asegúrate de que Docker esté corriendo: docker-compose up -d")
        return False

def test_templates_endpoint():
    """Verificar endpoint de plantillas"""
    try:
        response = requests.get(f"{BASE_URL}/templates")
        if response.status_code == 200:
            templates = response.json()
            print("\n✓ Plantillas disponibles en el sistema:")
            for tipo, info in templates.items():
                print(f"  - {tipo}: {', '.join(info['required_columns'])}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error obteniendo plantillas: {e}")
        return False

def validate_file(filepath, data_type):
    """Validar estructura de archivo"""
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                f"{BASE_URL}/validate",
                files={'file': f},
                data={'type': data_type}
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✓ Estructura válida: {result['rows']} filas")
            return True
        else:
            error = response.json()
            print(f"  ✗ Estructura inválida: {error.get('error')}")
            return False
    except Exception as e:
        print(f"  ✗ Error validando: {e}")
        return False

def upload_file(filepath, data_type):
    """Cargar archivo al sistema"""
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                f"{BASE_URL}/upload",
                files={'file': f},
                data={'type': data_type}
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✓ Cargado: {result['records']} registros insertados")
            return True
        else:
            error = response.json()
            print(f"  ✗ Error cargando: {error.get('error')}")
            return False
    except Exception as e:
        print(f"  ✗ Error en carga: {e}")
        return False

def get_stats():
    """Obtener estadísticas"""
    try:
        response = requests.get(f"{BASE_URL}/stats")
        if response.status_code == 200:
            stats = response.json()
            print("\n📊 Estadísticas actuales:")
            print(f"  Facturas: {stats['facturas']['total']} (Total: ${stats['facturas']['monto_total']})")
            print(f"  Cartera vencida: {stats['cartera_vencida']['vencidas']} (Total: ${stats['cartera_vencida']['monto_vencido']})")
            return True
        return False
    except Exception as e:
        print(f"✗ Error obteniendo estadísticas: {e}")
        return False

if __name__ == '__main__':
    print("🧪 Iniciando pruebas del sistema...\n")
    
    # 1. Verificar backend
    if not test_health():
        exit(1)
    
    # 2. Verificar endpoint de plantillas
    if not test_templates_endpoint():
        exit(1)
    
    # 3. Probar validación de archivos
    print("\n🔍 Validando plantillas...")
    
    templates_to_test = [
        ('plantilla_facturacion_diaria.xlsx', 'facturas'),
        ('plantilla_cartera_vencida.xlsx', 'cartera'),
        ('plantilla_ventas_productos.xlsx', 'productos'),
        ('plantilla_gastos_operativos.xlsx', 'gastos')
    ]
    
    for filename, data_type in templates_to_test:
        filepath = PLANTILLAS_DIR / filename
        if filepath.exists():
            print(f"\n{filename}:")
            print(f"  Tipo: {data_type}")
            validate_file(filepath, data_type)
        else:
            print(f"✗ No encontrado: {filepath}")
    
    # 4. Prueba opcional de carga (comentado por defecto)
    print("\n\n💡 Para probar la carga de datos:")
    print("   1. Abre las plantillas en Excel")
    print("   2. Llena la hoja 'Datos' con tus datos")
    print("   3. Guarda el archivo")
    print("   4. Descomenta la sección de prueba en este script")
    
    # Descomentar para probar carga real:
    # print("\n📤 Probando carga de archivos...")
    # for filename, data_type in templates_to_test:
    #     filepath = PLANTILLAS_DIR / filename
    #     if filepath.exists():
    #         print(f"\n{filename}:")
    #         upload_file(filepath, data_type)
    
    # 5. Ver estadísticas
    get_stats()
    
    print("\n✅ Pruebas completadas")
