# 🎯 GUÍA RÁPIDA - Sistema Dinámico de Reportes

## ⚡ Inicio Rápido (5 minutos)

### **Paso 1: Activar el nuevo sistema**

```bash
cd c:\Dev8n8\devprueba

# Reemplazar app.py con la versión dinámica
cd backend
move app.py app_old_backup.py
move app_new.py app.py

# Regresar y reiniciar
cd ..
docker-compose down
docker-compose up -d --build
```

### **Paso 2: Ejecutar migración**

```bash
# Esperar 30 segundos a que levanten los servicios
docker exec -it devprueba-backend python migrate_to_dynamic.py
```

Verás:

```
🚀 Iniciando migración a sistema dinámico...
📊 Creando tablas de metadatos...
✅ Tablas creadas correctamente

📝 Creando reportes de ejemplo...
  ✅ Facturación Diaria (ID: 1)
  ✅ Cartera Vencida (ID: 2)

✨ Migración completada!
```

### **Paso 3: Acceder al sistema**

**Panel de Administrador:**

```
http://localhost:5000/admin
```

**Portal de Usuario:**

```
http://localhost:5000
```

---

## 👨‍💼 Flujo de Trabajo ADMINISTRADOR

### **Crear un nuevo reporte (ejemplo real)**

1. Abrir `http://localhost:5000/admin`

2. Clic en "+ Crear Nuevo Reporte"

3. **Información básica:**
   - Nombre: `Ventas Diarias`
   - Código: `ventas_diarias` (sin espacios)
   - Categoría: `Ventas`
   - Icono: `💵`
   - Descripción: `Registro de ventas del día`

4. **Contexto (importante para IA):**

   ```
   Este reporte registra las ventas diarias de todos los puntos de venta.
   Incluye información del vendedor, cliente, productos y montos.
   Se relaciona con el catálogo de productos mediante codigo_producto.
   Los montos están en pesos colombianos.
   Usado para comisiones de vendedores y análisis de tendencias.
   ```

5. **Agregar campos** (clic "+ Agregar Campo"):

   **Campo 1:**
   - Nombre técnico: `fecha_venta`
   - Etiqueta: `Fecha de Venta`
   - Tipo: `Fecha`
   - Obligatorio: ✅
   - Descripción: `Fecha de la transacción`
   - Ejemplo: `2026-02-01`

   **Campo 2:**
   - Nombre técnico: `vendedor`
   - Etiqueta: `Nombre del Vendedor`
   - Tipo: `Texto`
   - Obligatorio: ✅
   - Ejemplo: `Juan Pérez`

   **Campo 3:**
   - Nombre técnico: `codigo_producto`
   - Etiqueta: `Código del Producto`
   - Tipo: `Texto`
   - Obligatorio: ✅
   - Ejemplo: `PROD-001`

   **Campo 4:**
   - Nombre técnico: `cantidad`
   - Etiqueta: `Cantidad Vendida`
   - Tipo: `Número`
   - Obligatorio: ✅
   - Ejemplo: `5`

   **Campo 5:**
   - Nombre técnico: `precio_unitario`
   - Etiqueta: `Precio Unitario`
   - Tipo: `Decimal`
   - Obligatorio: ✅
   - Ejemplo: `50000.00`

   **Campo 6:**
   - Nombre técnico: `total`
   - Etiqueta: `Total Venta`
   - Tipo: `Decimal`
   - Obligatorio: ✅
   - Ejemplo: `250000.00`

6. **(Opcional) Agregar relación:**
   - Reporte destino: `catalogo_productos`
   - Campo origen: `codigo_producto`
   - Campo destino: `codigo`
   - Descripción: `Vinculado al catálogo de productos`

7. **Guardar** → ¡Listo!

### **Resultado:**

✅ Reporte creado automáticamente  
✅ Plantilla Excel generada  
✅ Validación configurada  
✅ Disponible para usuarios

**Todo sin escribir una línea de código!** 🎉

---

## 👤 Flujo de Trabajo USUARIO

1. **Abrir** `http://localhost:5000`

2. **Ver reportes disponibles:**
   - Facturación Diaria 📊
   - Cartera Vencida 💰
   - Ventas Diarias 💵 (el que acabas de crear)

3. **Seleccionar** "Ventas Diarias"

4. **Leer contexto:**

   ```
   📖 Para qué sirve este reporte:
   Este reporte registra las ventas diarias de todos los
   puntos de venta. Incluye información del vendedor...
   ```

5. **Descargar plantilla** → Se descarga `plantilla_ventas_diarias.xlsx`

6. **Abrir Excel:**
   - **Hoja "Datos"**: Columnas vacías listas para llenar
   - **Hoja "Ejemplo"**: Fila de muestra
   - **Hoja "Instrucciones"**: Descripción de cada campo

7. **Completar datos** en hoja "Datos"

8. **Regresar a la web** y **arrastrar archivo**

9. **Clic** "📤 Subir Datos"

10. **Ver confirmación:**
    ```
    ✅ Se procesaron 25 registros correctamente
    ```

---

## 📊 Casos de Uso Reales

### **Caso 1: Empresa de Servicios**

**Admin crea:**

- `servicios_ejecutados`
- `tiempo_tecnicos`
- `materiales_usados`

**Usuarios cargan:**

- Servicios diarios
- Horas trabajadas
- Consumo de materiales

**IA analiza:**

- Rentabilidad por servicio
- Productividad de técnicos
- Control de inventario

### **Caso 2: Retail**

**Admin crea:**

- `ventas_caja`
- `inventario_tienda`
- `devoluciones`

**Usuarios cargan:**

- Cierre de caja diario
- Conteo físico
- Productos devueltos

**IA genera:**

- Proyecciones de stock
- Alertas de productos lentos
- Análisis de mermas

### **Caso 3: Manufactura**

**Admin crea:**

- `produccion_diaria`
- `consumo_materias_primas`
- `control_calidad`

**Usuarios cargan:**

- Unidades producidas
- Materiales consumidos
- Defectos detectados

**IA detecta:**

- Eficiencia de líneas
- Desperdicios anormales
- Patrones de defectos

---

## 🤖 Integración con IA

### **Cómo el contexto ayuda a los agentes:**

**Ejemplo - GPT analizando datos:**

```
Usuario: "¿Qué vendedor tuvo mejores ventas este mes?"

GPT:
1. Lee contexto de "ventas_diarias"
   → Sabe que campo "vendedor" identifica al vendedor
   → Sabe que "total" es el monto en pesos

2. Consulta datos del mes actual

3. Agrupa por vendedor

4. Retorna: "Juan Pérez lideró con $45,800,000 en ventas"
```

**Preguntas complejas:**

```
Usuario: "¿Hay productos con bajo movimiento que deberíamos descontinuar?"

GPT:
1. Lee contexto de "ventas_diarias"
   → Identifica campo "codigo_producto"

2. Lee contexto de "inventario_tienda"
   → Sabe relación con ventas

3. Analiza productos con <5 ventas/mes y >100 unidades stock

4. Retorna lista con recomendaciones
```

---

## ⚙️ Configuración Avanzada

### **Tipos de datos disponibles:**

- `texto` → VARCHAR(500)
- `numero` → INTEGER
- `decimal` → DECIMAL(15,2)
- `fecha` → DATE
- `booleano` → BOOLEAN
- `email` → VARCHAR(255)
- `telefono` → VARCHAR(20)

### **Validaciones futuras:**

- Regex personalizado
- Valores permitidos (select)
- Rangos numéricos
- Fechas min/max

### **Relaciones:**

- `referencia` - FK simple
- `agregacion` - Suma/promedio
- `jerarquia` - Padre/hijo

---

## 🔧 Troubleshooting

### **"No puedo acceder al admin"**

```bash
# Verificar que el backend esté corriendo
docker ps | grep backend

# Ver logs
docker logs devprueba-backend
```

### **"Error al crear reporte"**

- Verificar que el código no tenga espacios
- El código debe ser único
- Al menos un campo obligatorio

### **"Error al subir archivo"**

- Verificar que sea .xlsx
- Columnas deben coincidir exactamente
- Llenar campos obligatorios

### **"No se ve el reporte en usuario"**

- Verificar que esté marcado como "activo"
- Refrescar la página

---

## 📈 Roadmap

### **Versión Actual (2.0)**

✅ Sistema dinámico de reportes  
✅ Panel de administración  
✅ Portal de usuario  
✅ Contexto para IA  
✅ Relaciones entre reportes

### **Próxima Versión (2.1)**

- [ ] Autenticación de usuarios
- [ ] Permisos por reporte
- [ ] Dashboard de visualización
- [ ] Export a CSV/PDF
- [ ] Búsqueda avanzada de datos

### **Futuro (3.0)**

- [ ] IA integrada para análisis
- [ ] Predicciones automáticas
- [ ] Alertas inteligentes
- [ ] App móvil
- [ ] API pública

---

## 💡 Tips y Mejores Prácticas

### **Para Administradores:**

✅ **Escribe buen contexto:** Piensa que le explicas a un analista nuevo  
✅ **Nombra campos claros:** `numero_factura` mejor que `num_fact`  
✅ **Usa ejemplos reales:** Ayuda a los usuarios a entender  
✅ **Define relaciones:** Permite análisis cruzados  
✅ **Revisa datos:** Periódicamente verifica calidad

### **Para Usuarios:**

✅ **Lee el contexto:** Entiende para qué sirve el reporte  
✅ **Usa la hoja ejemplo:** Copia el formato exacto  
✅ **No cambies columnas:** Respeta la estructura  
✅ **Valida antes:** Revisa que los datos sean coherentes  
✅ **Sube periódicamente:** Mantén los datos actualizados

---

## 🎯 Conclusión

Has implementado un **sistema completamente dinámico** donde:

✨ **Sin código** - Todo por configuración  
✨ **Escalable** - Crece sin límites  
✨ **Inteligente** - Contexto para IA  
✨ **Simple** - Usuarios no técnicos  
✨ **Poderoso** - Relaciones complejas

**¡Ahora tu sistema puede crecer sin necesitar un desarrollador!** 🚀

---

## 📞 Soporte

¿Preguntas? Revisa:

- `SISTEMA_DINAMICO.md` - Documentación técnica completa
- `backend/models.py` - Modelos de datos
- `backend/db_manager.py` - API de base de datos
