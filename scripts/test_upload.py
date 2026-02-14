"""
Pruebas de carga y validación alineadas con los endpoints actuales.
Ejecutar: python test_upload.py
"""

import requests
import os
from pathlib import Path
import pandas as pd
import json

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

def listar_reportes_activos():
    """Listar reportes activos"""
    try:
        response = requests.get(f"{BASE_URL}/api/reportes")
        if response.status_code == 200:
            reportes = response.json()
            if not reportes:
                print("✗ No hay reportes activos.")
                return []
            print("\n✓ Reportes activos:")
            for r in reportes:
                estado = "activo" if r.get("activo") else "inactivo"
                print(f"  - {r.get('codigo')} ({estado}): {r.get('nombre')}")
            return reportes
        else:
            print(f"✗ Error listando reportes: {response.text}")
            return []
    except Exception as e:
        print(f"✗ Error conectando a /api/reportes: {e}")
        return []

def obtener_campos_reporte(codigo):
    """Obtener campos configurados o inferidos de un reporte"""
    try:
        response = requests.get(f"{BASE_URL}/api/reportes/{codigo}/campos")
        if response.status_code == 200:
            campos_raw = response.json()
            # Normalizar formatos posibles: lista de dicts, lista de strings o JSON string
            if isinstance(campos_raw, str):
                try:
                    campos = json.loads(campos_raw)
                except Exception:
                    campos = []
            else:
                campos = campos_raw
            # Convertir a lista de dicts uniforme
            campos_norm = []
            for c in campos:
                if isinstance(c, dict):
                    campos_norm.append(c)
                elif isinstance(c, str):
                    campos_norm.append({"nombre": c, "obligatorio": False})
            print("\n🔖 Campos del reporte:")
            for c in campos_norm:
                req = "(obligatorio)" if c.get("obligatorio") else ""
                print(f"  - {c.get('nombre')} {req}")
            return campos_norm
        else:
            print(f"✗ Error obteniendo campos: {response.text}")
            return []
    except Exception as e:
        print(f"✗ Error conectando a /api/reportes/{codigo}/campos: {e}")
        return []

def validar_local(filepath, codigo, campos):
    """Validar localmente que el Excel tiene los campos obligatorios."""
    try:
        # Preferir hoja 'Datos' ignorando mayúsculas/espacios; si no existe usar primera hoja
        xls = pd.ExcelFile(filepath)
        sheet_names = xls.sheet_names
        normalized = [s.strip().lower() for s in sheet_names]
        hoja = sheet_names[normalized.index('datos')] if 'datos' in normalized else sheet_names[0]
        df = xls.parse(sheet_name=hoja)
        print(f"\n📄 Usando hoja: {hoja} | Columnas: {', '.join(map(str, df.columns.tolist()))}")

        campos_obligatorios = [c['nombre'] for c in campos if c.get('obligatorio')]
        faltantes = [c for c in campos_obligatorios if c not in df.columns]
        if faltantes:
            print(f"  ✗ Faltan campos obligatorios: {', '.join(faltantes)}")
            return False
        print(f"  ✓ Estructura válida. Filas: {len(df)}")
        return True
    except Exception as e:
        print(f"  ✗ Error validando localmente: {e}")
        return False

def upload_file(filepath, codigo):
    """Cargar archivo al sistema para un reporte específico"""
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                f"{BASE_URL}/api/reportes/{codigo}/upload",
                files={'file': f}
            )
        
        if response.status_code == 200:
            result = response.json()
            registros = result.get('registros_insertados')
            if registros is None:
                registros = result.get('records')
            print(f"  ✓ Cargado: {registros} registros insertados")
            return True
        else:
            try:
                error = response.json().get('error')
            except Exception:
                error = response.text
            print(f"  ✗ Error cargando: {error}")
            return False
    except Exception as e:
        print(f"  ✗ Error en carga: {e}")
        return False

def get_stats(codigo):
    """Obtener estadísticas de un reporte"""
    try:
        response = requests.get(f"{BASE_URL}/api/reportes/{codigo}/estadisticas")
        if response.status_code == 200:
            stats = response.json()
            print("\n📊 Estadísticas del reporte:")
            for k, v in stats.items():
                print(f"  {k}: {v}")
            return True
        else:
            print(f"✗ Error obteniendo estadísticas: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error conectando a estadísticas: {e}")
        return False

if __name__ == '__main__':
    print("🧪 Iniciando pruebas del sistema...\n")

    # 1. Verificar backend
    if not test_health():
        exit(1)

    # 2. Listar reportes activos y elegir uno
    reportes = listar_reportes_activos()
    if not reportes:
        exit(1)
    codigo = reportes[0].get('codigo')
    nombre = reportes[0].get('nombre')
    print(f"\n➡️ Usando reporte: {codigo} - {nombre}")

    # 3. Obtener campos y validar localmente el primer archivo encontrado
    campos = obtener_campos_reporte(codigo)
    archivos = list(PLANTILLAS_DIR.glob('*.xls*'))
    if not archivos:
        print(f"✗ No se encontraron archivos en {PLANTILLAS_DIR}. Coloca tu Excel allí.")
        exit(1)
    filepath = archivos[0]
    print(f"\n🔍 Validando archivo: {filepath.name}")
    validar_local_ok = validar_local(filepath, codigo, campos)

    # 4. Carga de datos si la validación local pasó
    if validar_local_ok:
        print("\n📤 Subiendo archivo...")
        upload_file(filepath, codigo)

    # 5. Ver estadísticas
    get_stats(codigo)

    print("\n✅ Pruebas completadas")
