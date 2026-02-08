"""
Script para generar informe de facturación semanal con gráficos y Excel
"""
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
from io import BytesIO
import base64

# Configuración
BASE_URL = "http://localhost:5000"

# Estilo de gráficos
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

def obtener_datos_facturacion():
    """Obtener datos de facturación desde la API"""
    print("📊 Obteniendo reportes disponibles...")
    r = requests.get(f"{BASE_URL}/api/admin/reportes")
    reportes = r.json()
    
    # Buscar reporte de facturación
    reporte_fact = None
    for rep in reportes:
        if 'factura' in rep['codigo'].lower() or 'factura' in rep['nombre'].lower():
            reporte_fact = rep
            break
    
    if not reporte_fact:
        print("❌ No se encontró reporte de facturación")
        return None, None
    
    print(f"✅ Reporte encontrado: {reporte_fact['nombre']} ({reporte_fact['codigo']})")
    
    # Obtener datos
    print("📥 Consultando datos...")
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    url = f"{BASE_URL}/api/query/{reporte_fact['codigo']}"
    params = {
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'limite': 10000
    }
    
    r = requests.get(url, params=params)
    resultado = r.json()
    
    if not resultado.get('success'):
        print(f"❌ Error obteniendo datos: {resultado.get('error')}")
        return None, None
    
    datos = resultado.get('datos', [])
    print(f"✅ {len(datos)} registros obtenidos")
    
    return datos, reporte_fact

def procesar_datos(datos):
    """Procesar datos y crear DataFrame"""
    if not datos:
        return None
    
    # Extraer datos JSONB
    registros = []
    for item in datos:
        datos_dict = item.get('datos', {})
        datos_dict['id'] = item.get('id')
        datos_dict['fecha_carga'] = item.get('created_at')
        registros.append(datos_dict)
    
    df = pd.DataFrame(registros)
    
    # Identificar campos relevantes
    print(f"\n📋 Columnas disponibles: {list(df.columns)}")
    
    # Intentar encontrar campos de tercero y monto
    tercero_col = None
    monto_col = None
    fecha_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'tercero' in col_lower or 'cliente' in col_lower or 'razon' in col_lower:
            tercero_col = col
        if 'monto' in col_lower or 'valor' in col_lower or 'total' in col_lower:
            monto_col = col
        if 'fecha' in col_lower and col != 'fecha_carga':
            fecha_col = col
    
    print(f"✅ Campo tercero: {tercero_col}")
    print(f"✅ Campo monto: {monto_col}")
    print(f"✅ Campo fecha: {fecha_col}")
    
    return df, tercero_col, monto_col, fecha_col

def generar_graficos(df, tercero_col, monto_col, fecha_col):
    """Generar gráficos de análisis"""
    if df is None or df.empty:
        print("❌ No hay datos para graficar")
        return None
    
    print("\n📊 Generando gráficos...")
    
    # Crear figura con múltiples subplots
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('INFORME DE FACTURACIÓN SEMANAL', fontsize=16, fontweight='bold')
    
    # Convertir monto a numérico
    df[monto_col] = pd.to_numeric(df[monto_col], errors='coerce')
    
    # 1. Top 10 Terceros por Facturación
    top_terceros = df.groupby(tercero_col)[monto_col].sum().sort_values(ascending=False).head(10)
    ax1 = axes[0, 0]
    top_terceros.plot(kind='barh', ax=ax1, color='steelblue')
    ax1.set_title('Top 10 Terceros por Facturación', fontweight='bold', fontsize=12)
    ax1.set_xlabel('Monto Total ($)')
    ax1.set_ylabel('Tercero')
    ax1.grid(True, alpha=0.3)
    
    # Agregar valores en las barras
    for i, v in enumerate(top_terceros.values):
        ax1.text(v, i, f' ${v:,.0f}', va='center')
    
    # 2. Distribución de Montos por Tercero (Box Plot)
    ax2 = axes[0, 1]
    top_10_nombres = top_terceros.index.tolist()
    df_top10 = df[df[tercero_col].isin(top_10_nombres)]
    
    if len(df_top10) > 0:
        df_top10.boxplot(column=monto_col, by=tercero_col, ax=ax2)
        ax2.set_title('Distribución de Montos por Tercero', fontweight='bold', fontsize=12)
        ax2.set_xlabel('Tercero')
        ax2.set_ylabel('Monto ($)')
        ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')
        plt.sca(ax2)
        plt.xticks(rotation=45, ha='right')
    
    # 3. Cantidad de Facturas por Tercero
    ax3 = axes[1, 0]
    cant_facturas = df.groupby(tercero_col).size().sort_values(ascending=False).head(10)
    cant_facturas.plot(kind='bar', ax=ax3, color='coral')
    ax3.set_title('Cantidad de Facturas por Tercero', fontweight='bold', fontsize=12)
    ax3.set_xlabel('Tercero')
    ax3.set_ylabel('Cantidad de Facturas')
    ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45, ha='right')
    ax3.grid(True, alpha=0.3)
    
    # 4. Participación Porcentual
    ax4 = axes[1, 1]
    top_5 = df.groupby(tercero_col)[monto_col].sum().sort_values(ascending=False).head(5)
    otros = df.groupby(tercero_col)[monto_col].sum().sum() - top_5.sum()
    
    participacion = list(top_5.values) + [otros]
    labels = list(top_5.index) + ['Otros']
    
    colors = sns.color_palette('Set3', len(participacion))
    ax4.pie(participacion, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
    ax4.set_title('Participación por Tercero (Top 5)', fontweight='bold', fontsize=12)
    
    plt.tight_layout()
    
    # Guardar imagen
    output_dir = 'data/informes'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    img_path = f'{output_dir}/informe_facturacion_{timestamp}.png'
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    print(f"✅ Gráfico guardado: {img_path}")
    
    return img_path

def generar_excel(df, tercero_col, monto_col, fecha_col):
    """Generar archivo Excel con análisis detallado"""
    if df is None or df.empty:
        print("❌ No hay datos para Excel")
        return None
    
    print("\n📑 Generando archivo Excel...")
    
    output_dir = 'data/informes'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_path = f'{output_dir}/facturacion_detallada_{timestamp}.xlsx'
    
    # Crear Excel con múltiples hojas
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Hoja 1: Datos completos
        df.to_excel(writer, sheet_name='Datos Completos', index=False)
        
        # Hoja 2: Resumen por Tercero
        resumen = df.groupby(tercero_col).agg({
            monto_col: ['sum', 'mean', 'count', 'min', 'max']
        }).round(2)
        resumen.columns = ['Total Facturado', 'Promedio', 'Cantidad', 'Mínimo', 'Máximo']
        resumen = resumen.sort_values('Total Facturado', ascending=False)
        resumen.to_excel(writer, sheet_name='Resumen por Tercero')
        
        # Hoja 3: Top 20 Terceros
        top_20 = df.groupby(tercero_col)[monto_col].sum().sort_values(ascending=False).head(20)
        top_20_df = pd.DataFrame({
            'Tercero': top_20.index,
            'Monto Total': top_20.values,
            'Porcentaje': (top_20.values / top_20.sum() * 100).round(2)
        })
        top_20_df.to_excel(writer, sheet_name='Top 20 Terceros', index=False)
        
        # Hoja 4: Estadísticas Generales
        stats = pd.DataFrame({
            'Métrica': [
                'Total Facturado',
                'Promedio por Factura',
                'Cantidad de Facturas',
                'Cantidad de Terceros Únicos',
                'Factura Máxima',
                'Factura Mínima'
            ],
            'Valor': [
                f"${df[monto_col].sum():,.2f}",
                f"${df[monto_col].mean():,.2f}",
                len(df),
                df[tercero_col].nunique(),
                f"${df[monto_col].max():,.2f}",
                f"${df[monto_col].min():,.2f}"
            ]
        })
        stats.to_excel(writer, sheet_name='Estadísticas', index=False)
    
    print(f"✅ Excel guardado: {excel_path}")
    
    return excel_path

def generar_informe_texto(df, tercero_col, monto_col):
    """Generar informe en texto"""
    if df is None or df.empty:
        return "No hay datos disponibles"
    
    total = df[monto_col].sum()
    promedio = df[monto_col].mean()
    terceros = df[tercero_col].nunique()
    facturas = len(df)
    
    top_3 = df.groupby(tercero_col)[monto_col].sum().sort_values(ascending=False).head(3)
    
    informe = f"""
╔══════════════════════════════════════════════════════════════╗
║       INFORME DE FACTURACIÓN SEMANAL POR TERCERO            ║
╚══════════════════════════════════════════════════════════════╝

📅 Período: Última semana
📊 Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

═══════════════════════════════════════════════════════════════
                    RESUMEN EJECUTIVO
═══════════════════════════════════════════════════════════════

💰 Total Facturado:          ${total:,.2f}
📈 Promedio por Factura:     ${promedio:,.2f}
📋 Cantidad de Facturas:     {facturas:,}
👥 Terceros Únicos:          {terceros:,}

═══════════════════════════════════════════════════════════════
                    TOP 3 TERCEROS
═══════════════════════════════════════════════════════════════
"""
    
    for i, (tercero, monto) in enumerate(top_3.items(), 1):
        porcentaje = (monto / total * 100)
        informe += f"\n{i}. {tercero}\n"
        informe += f"   Monto: ${monto:,.2f} ({porcentaje:.1f}%)\n"
    
    informe += "\n═══════════════════════════════════════════════════════════════\n"
    
    return informe

def main():
    """Función principal"""
    print("="*70)
    print("  GENERADOR DE INFORME DE FACTURACIÓN SEMANAL POR TERCERO")
    print("="*70)
    
    # 1. Obtener datos
    datos, reporte = obtener_datos_facturacion()
    if not datos:
        print("❌ No se pudieron obtener datos")
        return
    
    # 2. Procesar datos
    df, tercero_col, monto_col, fecha_col = procesar_datos(datos)
    if df is None or df.empty:
        print("❌ No hay datos para procesar")
        return
    
    # 3. Generar informe de texto
    informe_texto = generar_informe_texto(df, tercero_col, monto_col)
    print(informe_texto)
    
    # 4. Generar gráficos
    img_path = generar_graficos(df, tercero_col, monto_col, fecha_col)
    
    # 5. Generar Excel
    excel_path = generar_excel(df, tercero_col, monto_col, fecha_col)
    
    print("\n" + "="*70)
    print("  INFORME GENERADO EXITOSAMENTE")
    print("="*70)
    print(f"\n📊 Gráficos: {img_path}")
    print(f"📑 Excel: {excel_path}")
    print("\n¡Revisa los archivos generados en la carpeta data/informes/!\n")

if __name__ == "__main__":
    main()
