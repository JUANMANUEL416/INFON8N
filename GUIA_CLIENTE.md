# 🌐 Guía del Cliente - Sistema de Carga de Informes

## 📝 Flujo de Trabajo Completo

### Para el **Desarrollador** (tú):

1. ✅ **Crear las plantillas fijas** (solo una vez)

   ```bash
   cd scripts
   python create_templates.py
   ```

2. ✅ **Iniciar el sistema**

   ```bash
   docker-compose up -d
   ```

3. ✅ **Compartir URL con el cliente**
   - URL: `http://localhost:5000`
   - (O configurar para acceso remoto si es necesario)

---

### Para el **Cliente** (usuario final):

#### 📥 **Paso 1: Descargar Plantilla**

1. Abrir navegador en: `http://localhost:5000`
2. Ir a la sección **"Descargar Plantillas"**
3. Hacer clic en la plantilla que necesite:
   - 📊 **Facturación Diaria**
   - 💰 **Cartera Vencida**
   - 📦 **Ventas Productos**
   - 💸 **Gastos Operativos**

4. El archivo `.xlsx` se descarga automáticamente

#### ✏️ **Paso 2: Completar la Plantilla**

1. Abrir el archivo descargado con **Excel**
2. Ver la hoja **"Ejemplo"** para entender el formato
3. Ver la hoja **"Validaciones"** para conocer los campos
4. **Llenar la hoja "Datos"** con su información
5. **Guardar el archivo**

⚠️ **Importante:**

- NO cambiar nombres de columnas
- NO agregar columnas extra
- Respetar los formatos (fechas, números)

#### 📤 **Paso 3: Subir el Archivo**

1. Volver a: `http://localhost:5000`
2. Ir a la sección **"Subir Archivo Completado"**
3. Seleccionar el **tipo de datos** en el menú desplegable
4. **Arrastrar el archivo** al área de carga (o hacer clic para seleccionar)
5. Hacer clic en **"Subir Archivo"**
6. Esperar confirmación ✅

#### 📊 **Paso 4: Ver Resultados**

1. En la misma página, ir a **"Estadísticas del Sistema"**
2. Hacer clic en **"Actualizar Estadísticas"**
3. Ver:
   - Total de facturas
   - Cartera vencida
   - Productos registrados
   - Gastos totales

---

## 🎯 Ventajas para el Cliente

✅ **Súper simple** - No necesita saber programación
✅ **Interfaz visual** - Todo desde el navegador
✅ **Validación automática** - El sistema verifica que todo esté correcto
✅ **Inmediato** - Ve los resultados al instante
✅ **Seguro** - Los datos quedan en la base de datos

---

## 🖼️ Capturas Conceptuales

### Vista Principal

```
┌─────────────────────────────────────────────────┐
│  📊 Sistema de Carga de Informes Gerenciales   │
│      Cargue sus datos de forma sencilla        │
├─────────────────────────────────────────────────┤
│                                                 │
│  📥 1. DESCARGAR PLANTILLAS                    │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐       │
│  │  📊  │  │  💰  │  │  📦  │  │  💸  │       │
│  │Factu │  │Carter│  │Ventas│  │Gastos│       │
│  │ [⬇] │  │ [⬇]  │  │ [⬇]  │  │ [⬇]  │       │
│  └──────┘  └──────┘  └──────┘  └──────┘       │
│                                                 │
│  📤 2. SUBIR ARCHIVO                           │
│  Tipo: [Facturación ▼]                         │
│  ┌─────────────────────────────┐               │
│  │  📁 Arrastre archivo aquí  │               │
│  │  o haga clic para           │               │
│  │  seleccionar                │               │
│  └─────────────────────────────┘               │
│                                                 │
│  📈 3. ESTADÍSTICAS                            │
│  [Actualizar]                                  │
│  ┌────────────────────────────────┐            │
│  │ Facturas: 150  ($450,000)      │            │
│  │ Cartera: 25    ($75,000)       │            │
│  └────────────────────────────────┘            │
└─────────────────────────────────────────────────┘
```

---

## 🔧 Personalización (Desarrollador)

### Cambiar Puerto

En `docker-compose.yml`:

```yaml
ports:
  - "8080:5000" # Cambiar 5000 a otro puerto
```

### Agregar Nueva Plantilla

1. Editar `scripts/create_templates.py`
2. Agregar nueva entrada en diccionario `TEMPLATES`
3. Actualizar `backend/app.py` → `DATA_MODELS`
4. Crear tabla en base de datos
5. Regenerar plantillas

### Personalizar Interfaz

- **Colores**: Editar `backend/static/style.css`
- **Textos**: Editar `backend/templates/index.html`
- **Logo**: Agregar imagen en `backend/static/`

---

## 📞 Soporte

Si el cliente tiene problemas:

1. **Verificar que Docker esté corriendo**

   ```bash
   docker-compose ps
   ```

2. **Ver logs del backend**

   ```bash
   docker-compose logs -f backend
   ```

3. **Reiniciar servicios**

   ```bash
   docker-compose restart
   ```

4. **Verificar conectividad**
   - Abrir: `http://localhost:5000/health`
   - Debe mostrar: `{"status":"ok"}`

---

## 🚀 Puesta en Producción

Para que el cliente acceda desde otras computadoras:

1. **Opción 1: Red Local**
   - Cambiar `localhost` por IP de la máquina
   - Ejemplo: `http://192.168.1.100:5000`

2. **Opción 2: Túnel con ngrok** (para demo)

   ```bash
   ngrok http 5000
   ```

3. **Opción 3: Servidor dedicado**
   - Desplegar en VPS/Cloud
   - Configurar dominio
   - Agregar HTTPS

---

## ✨ Próximas Mejoras Sugeridas

- [ ] Autenticación de usuarios
- [ ] Historial de cargas
- [ ] Exportar reportes en PDF
- [ ] Gráficos y dashboards
- [ ] Notificaciones por email
- [ ] App móvil (PWA)
