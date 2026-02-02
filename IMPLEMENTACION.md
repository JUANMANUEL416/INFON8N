# 🎯 Sistema de Plantillas Fijas - Implementación Completada

## ✅ Lo que se ha implementado

### 1. **Script Generador de Plantillas** ([scripts/create_templates.py](scripts/create_templates.py))

Genera automáticamente 4 plantillas Excel con estructura fija:

- ✅ **plantilla_facturacion_diaria.xlsx** - Facturación diaria
- ✅ **plantilla_cartera_vencida.xlsx** - Cartera vencida
- ✅ **plantilla_ventas_productos.xlsx** - Ventas por producto
- ✅ **plantilla_gastos_operativos.xlsx** - Gastos operativos

Cada plantilla incluye 3 hojas:

- **Datos**: Hoja vacía para ingresar información
- **Ejemplo**: Fila de ejemplo con formato correcto
- **Validaciones**: Descripción de cada campo

### 2. **Backend Mejorado** ([backend/app.py](backend/app.py))

**Nuevas funcionalidades:**

✅ **Validación de estructura** - Verifica columnas antes de cargar

```python
validate_excel_structure(df, data_type)
```

✅ **Nuevos endpoints:**

- `GET /templates` - Lista plantillas disponibles
- `POST /validate` - Valida archivo sin guardarlo

✅ **Soporte para 4 tipos de datos:**

- `facturas` → tabla facturas
- `cartera` → tabla cartera
- `productos` → tabla productos (nueva)
- `gastos` → tabla gastos (nueva)

✅ **Nuevas tablas en PostgreSQL:**

```sql
CREATE TABLE productos (...)
CREATE TABLE gastos (...)
```

### 3. **Documentación Completa**

✅ [data/plantillas/README.md](data/plantillas/README.md) - Guía de uso de plantillas
✅ [README.md](README.md) - Actualizado con instrucciones
✅ [scripts/test_upload.py](scripts/test_upload.py) - Script de pruebas

## 🚀 Cómo usar el sistema

### Paso 1: Generar plantillas (ya hecho)

```bash
cd scripts
python create_templates.py
```

### Paso 2: Iniciar servicios

```bash
docker-compose up -d
```

### Paso 3: Usar plantillas

1. **Abrir plantilla** en `data/plantillas/`
2. **Revisar hoja "Ejemplo"** para ver formato correcto
3. **Llenar hoja "Datos"** con tu información
4. **Guardar archivo**

### Paso 4: Validar (opcional pero recomendado)

```bash
curl -X POST http://localhost:5000/validate \
  -F "file=@data/plantillas/plantilla_facturacion_diaria.xlsx" \
  -F "type=facturas"
```

### Paso 5: Cargar datos

```bash
curl -X POST http://localhost:5000/upload \
  -F "file=@data/plantillas/plantilla_facturacion_diaria.xlsx" \
  -F "type=facturas"
```

### Paso 6: Ver estadísticas

```bash
curl http://localhost:5000/stats
```

## 📋 Estructura de cada plantilla

### Facturación Diaria

| Campo          | Tipo    | Obligatorio | Ejemplo                  |
| -------------- | ------- | ----------- | ------------------------ |
| numero_factura | Texto   | ✅          | FAC-2024-0001            |
| fecha          | Fecha   | ✅          | 2024-02-01               |
| cliente        | Texto   | ✅          | Empresa ABC              |
| monto          | Decimal | ✅          | 1500.50                  |
| estado         | Texto   | ❌          | pendiente/pagada/vencida |

### Cartera Vencida

| Campo          | Tipo    | Obligatorio | Ejemplo         |
| -------------- | ------- | ----------- | --------------- |
| numero_factura | Texto   | ❌          | FAC-2024-0001   |
| cliente        | Texto   | ✅          | Empresa ABC     |
| monto_adeudado | Decimal | ✅          | 2500.00         |
| dias_vencido   | Entero  | ❌          | 15              |
| estado         | Texto   | ❌          | vigente/vencida |

### Ventas Productos

| Campo            | Tipo    | Obligatorio | Ejemplo    |
| ---------------- | ------- | ----------- | ---------- |
| id_producto      | Texto   | ✅          | PROD-1001  |
| nombre           | Texto   | ✅          | Producto X |
| cantidad_vendida | Entero  | ✅          | 10         |
| precio_unitario  | Decimal | ✅          | 150.00     |
| fecha            | Fecha   | ✅          | 2024-02-01 |

### Gastos Operativos

| Campo       | Tipo    | Obligatorio | Ejemplo               |
| ----------- | ------- | ----------- | --------------------- |
| fecha       | Fecha   | ✅          | 2024-02-01            |
| categoria   | Texto   | ✅          | Servicios/Materiales  |
| descripcion | Texto   | ✅          | Descripción del gasto |
| monto       | Decimal | ✅          | 500.00                |
| area        | Texto   | ✅          | Administración        |

## 🧪 Probar el sistema

```bash
cd scripts
python test_upload.py
```

Este script:

1. ✅ Verifica que el backend esté funcionando
2. ✅ Lista plantillas disponibles
3. ✅ Valida estructura de cada plantilla
4. ✅ Muestra estadísticas actuales

## 🔄 Integración con n8n

Los workflows de n8n pueden usar estas plantillas:

1. **workflow-webhook-upload.json** - Recibe archivos vía webhook
2. **workflow-carga-archivos.json** - Carga automática desde carpeta

Ambos ahora validan la estructura antes de procesar.

## ⚠️ Reglas importantes

1. **NO cambiar nombres de columnas** en la hoja "Datos"
2. **Respetar tipos de datos** (fechas, números, texto)
3. **NO agregar columnas extra**
4. **Llenar solo la hoja "Datos"**
5. **Usar el endpoint /validate** antes de cargar datos importantes

## 📊 Ventajas del sistema

✅ **Estructura consistente** - Siempre el mismo formato
✅ **Validación automática** - Detecta errores antes de cargar
✅ **Documentación incluida** - Cada plantilla tiene ejemplos
✅ **Escalable** - Fácil agregar nuevas plantillas
✅ **Compatible con n8n** - Workflows listos para usar

## 🛠️ Próximas mejoras sugeridas

- [ ] Validación de tipos de datos (fechas, números)
- [ ] Mensajes de error más descriptivos
- [ ] Dashboard web para visualizar datos
- [ ] Exportar reportes en PDF
- [ ] Integración con API de IA para análisis
