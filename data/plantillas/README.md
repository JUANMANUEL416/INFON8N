# 📋 Plantillas de Datos - Sistema de Informes

## ¿Qué son las plantillas?

Las plantillas son archivos Excel con estructura fija que garantizan que los datos se carguen correctamente al sistema.

## 📁 Plantillas Disponibles

### plantilla_facturacion_diaria.xlsx

**Descripción:** Facturación diaria - campos obligatorios

**Columnas obligatorias:**

| Campo | Descripción |
|-------|-------------|
| `numero_factura` | Texto único (ej: FAC-2024-0001) |
| `fecha` | Fecha (YYYY-MM-DD) |
| `cliente` | Texto (nombre del cliente) |
| `monto` | Número decimal (ej: 1500.50) |
| `estado` | pendiente|pagada|vencida |

**Archivo:** `plantilla_facturacion_diaria.xlsx`

---

### plantilla_cartera_vencida.xlsx

**Descripción:** Cartera vencida - seguimiento de cuentas por cobrar

**Columnas obligatorias:**

| Campo | Descripción |
|-------|-------------|
| `numero_factura` | Texto (ej: FAC-2024-0001) - opcional |
| `cliente` | Texto (nombre del cliente) |
| `monto_adeudado` | Número decimal |
| `dias_vencido` | Número entero (días) |
| `estado` | vigente|vencida|proxima_vencer |

**Archivo:** `plantilla_cartera_vencida.xlsx`

---

### plantilla_ventas_productos.xlsx

**Descripción:** Ventas por producto

**Columnas obligatorias:**

| Campo | Descripción |
|-------|-------------|
| `id_producto` | Texto único (ej: PROD-1001) |
| `nombre` | Texto (nombre del producto) |
| `cantidad_vendida` | Número entero |
| `precio_unitario` | Número decimal |
| `fecha` | Fecha (YYYY-MM-DD) |

**Archivo:** `plantilla_ventas_productos.xlsx`

---

### plantilla_gastos_operativos.xlsx

**Descripción:** Gastos operativos diarios

**Columnas obligatorias:**

| Campo | Descripción |
|-------|-------------|
| `fecha` | Fecha (YYYY-MM-DD) |
| `categoria` | Servicios|Materiales|Personal|Otros |
| `descripcion` | Texto descriptivo |
| `monto` | Número decimal |
| `area` | Texto (departamento/área) |

**Archivo:** `plantilla_gastos_operativos.xlsx`

---

## 🚀 Cómo usar las plantillas

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
curl -X POST http://localhost:5000/upload \
  -F "file=@plantilla_facturacion_diaria.xlsx" \
  -F "type=facturas"
```

## 🔍 Tipos de datos soportados

| Tipo en API | Plantilla recomendada |
|-------------|-----------------------|
| `facturas` | plantilla_facturacion_diaria.xlsx |
| `cartera` | plantilla_cartera_vencida.xlsx |
| `productos` | plantilla_ventas_productos.xlsx |
| `gastos` | plantilla_gastos_operativos.xlsx |
