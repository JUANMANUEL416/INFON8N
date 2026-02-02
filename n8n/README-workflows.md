# Workflows de n8n para Sistema de Informes

## 📁 Workflows Disponibles

### 1. **workflow-carga-archivos.json**

Carga automática de archivos Excel desde la carpeta `data/`

**Funcionalidad:**

- ✅ Busca archivos .xlsx en `/app/data`
- ✅ Detecta automáticamente si es factura o cartera
- ✅ Carga al backend
- ✅ Muestra estadísticas actualizadas

**Trigger:** Manual

---

### 2. **workflow-webhook-upload.json**

Endpoint webhook para recibir archivos Excel vía HTTP

**Funcionalidad:**

- ✅ Expone webhook en `/webhook/upload-excel`
- ✅ Recibe archivos por POST
- ✅ Procesa y carga a base de datos
- ✅ Responde con resultado JSON

**Trigger:** Webhook

**URL de prueba:**

```bash
curl -X POST http://localhost:5678/webhook/upload-excel?type=facturas \
  -F "file=@data/facturas_ejemplo.xlsx"
```

---

### 3. **workflow-reporte-diario.json**

Generación automática de reportes diarios

**Funcionalidad:**

- ✅ Se ejecuta todos los días a las 9 AM
- ✅ Obtiene estadísticas del backend
- ✅ Genera reporte formateado
- ✅ Calcula indicadores (% cartera vencida, etc.)

**Trigger:** Cron (9:00 AM diario)

---

## 🚀 Cómo Importar los Workflows

### **Opción 1: Desde la interfaz de n8n**

1. Abre n8n: http://localhost:5678
2. Inicia sesión (admin / admin123)
3. Haz clic en el menú de hamburguesa (☰) → **Workflows**
4. Clic en **Import from File**
5. Selecciona uno de los archivos JSON de la carpeta `n8n/`
6. Clic en **Import**

### **Opción 2: Copiando archivos al contenedor**

```powershell
# Copiar workflows al contenedor de n8n
docker cp n8n/workflow-carga-archivos.json devprueba-n8n:/tmp/
docker cp n8n/workflow-webhook-upload.json devprueba-n8n:/tmp/
docker cp n8n/workflow-reporte-diario.json devprueba-n8n:/tmp/
```

Luego importa desde n8n interface → Import from File → `/tmp/workflow-xxx.json`

---

## 🧪 Probar los Workflows

### **Test 1: Carga Manual**

1. Importa `workflow-carga-archivos.json`
2. Abre el workflow
3. Clic en **Execute Workflow** (botón de play)
4. Verifica que se carguen los archivos

### **Test 2: Webhook**

1. Importa `workflow-webhook-upload.json`
2. Activa el workflow (toggle en la esquina superior derecha)
3. Copia la URL del webhook
4. Prueba con curl:
   ```powershell
   curl -X POST http://localhost:5678/webhook/upload-excel?type=facturas -F "file=@data/facturas_ejemplo.xlsx"
   ```

### **Test 3: Reporte Programado**

1. Importa `workflow-reporte-diario.json`
2. Para probar inmediatamente, cambia el cron a `* * * * *` (cada minuto)
3. Activa el workflow
4. Espera 1 minuto y verifica la ejecución en **Executions**

---

## 📊 Extender los Workflows

### Añadir notificaciones por email:

Agrega nodo **Send Email** después de "Generar Reporte"

### Integrar con Slack:

Agrega nodo **Slack** para enviar reportes al canal

### Guardar en Google Sheets:

Agrega nodo **Google Sheets** para exportar estadísticas

### Alertas de cartera crítica:

Añade nodo **IF** para detectar cuando cartera vencida > 40%

---

## 🔧 Troubleshooting

**Error: "Cannot connect to backend:5000"**

- Verifica que el contenedor backend esté corriendo: `docker-compose ps`
- Usa `http://backend:5000` (nombre del servicio, no localhost)

**Webhook no responde**

- Asegúrate de activar el workflow (toggle ON)
- Verifica la URL completa en las propiedades del webhook

**Archivos no se encuentran**

- La ruta debe ser `/app/data` dentro del contenedor
- Verifica con: `docker exec devprueba-n8n ls /app/data`

---

## 📝 Próximos Workflows (Ideas)

- [ ] Validación de datos antes de cargar
- [ ] Backup automático de base de datos
- [ ] Análisis de tendencias mensuales
- [ ] Detección de duplicados
- [ ] Envío de recordatorios a clientes morosos
