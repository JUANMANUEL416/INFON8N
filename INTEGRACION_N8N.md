# 🔗 Guía de Integración con n8n

## Endpoints Disponibles

### 1. Consultar Datos (GET)

```
GET http://localhost:5000/api/query/{codigo_reporte}
```

**Parámetros opcionales:**

- `fecha_inicio` (YYYY-MM-DD): Filtrar desde fecha
- `fecha_fin` (YYYY-MM-DD): Filtrar hasta fecha
- `limite` (número): Límite de registros (default: 100)

**Ejemplo:**

```bash
curl "http://localhost:5000/api/query/facturacion%20emitida%20de%20manera%20unitaria?limite=50"
```

**Respuesta:**

```json
{
  "success": true,
  "reporte": "Facturación Emitida",
  "total": 2883,
  "datos": [
    {
      "id": 1,
      "datos": {
        "fecha": "2024-01-15",
        "monto": 1500.5,
        "cliente": "Cliente A"
      },
      "created_at": "2026-02-08T09:54:24",
      "uploaded_by": "usuario"
    }
  ]
}
```

### 2. Exportar a Excel (GET)

```
GET http://localhost:5000/api/query/{codigo_reporte}/export
```

**Parámetros opcionales:** Mismos que consulta

**Ejemplo:**

```bash
curl -O "http://localhost:5000/api/query/facturacion%20emitida%20de%20manera%20unitaria/export"
```

### 3. Webhook - Cargar Datos (POST)

```
POST http://localhost:5000/webhook/upload/{codigo_reporte}
```

**Body (JSON):**

```json
{
  "datos": [
    {
      "fecha": "2024-01-15",
      "monto": 1500.5,
      "cliente": "Cliente A"
    },
    {
      "fecha": "2024-01-16",
      "monto": 2300.0,
      "cliente": "Cliente B"
    }
  ]
}
```

**O directamente un array:**

```json
[
  {
    "fecha": "2024-01-15",
    "monto": 1500.5
  }
]
```

**Respuesta:**

```json
{
  "success": true,
  "reporte": "Facturación Emitida",
  "registros_insertados": 2,
  "registros_error": 0,
  "mensaje": "Se procesaron 2 registros correctamente"
}
```

## Workflows de Ejemplo

### Workflow 1: Consulta Programada

Archivo: `n8n/workflow-consulta-datos.json`

Este workflow:

1. Se ejecuta cada hora (o según configuración)
2. Consulta los datos del reporte
3. Procesa la información
4. Puede enviarla por email, Slack, etc.

**Para importar:**

1. Ir a n8n (http://localhost:5678)
2. Click en "Workflows" → "Import from File"
3. Seleccionar `n8n/workflow-consulta-datos.json`

### Workflow 2: Recibir Datos via Webhook

Archivo: `n8n/workflow-webhook-recibir.json`

Este workflow:

1. Expone un webhook para recibir datos externos
2. Transforma los datos al formato del reporte
3. Los envía al sistema
4. Responde con el resultado

**Para usar:**

1. Importar el workflow
2. Activar el workflow
3. Copiar la URL del webhook
4. Enviar datos POST a esa URL

## Casos de Uso Comunes

### 1. Sincronizar con Google Sheets

```
Trigger: Cada 30 minutos
→ Leer Google Sheets
→ Transformar datos
→ POST a webhook/upload/{codigo}
```

### 2. Alertas por Email

```
Trigger: Cada día a las 8am
→ GET api/query/{codigo}?fecha_inicio=hoy
→ Filtrar registros importantes
→ Enviar email con resumen
```

### 3. Integración con CRM

```
Webhook Trigger (desde CRM)
→ Formatear datos
→ POST a webhook/upload/{codigo}
→ Responder al CRM
```

### 4. Backup Automático

```
Trigger: Cada domingo
→ GET api/query/{codigo}/export
→ Guardar en Google Drive / Dropbox
```

## Configuración en n8n

### Variables de Entorno Recomendadas

```env
BACKEND_URL=http://backend:5000
POSTGRES_HOST=postgres
POSTGRES_DB=reportes_db
```

### Nodos Útiles

- **HTTP Request**: Para consultar/enviar datos
- **Schedule Trigger**: Para ejecuciones programadas
- **Webhook**: Para recibir datos externos
- **Code**: Para transformar datos
- **Postgres**: Para consultas directas a la BD
- **Google Sheets**: Integración con hojas de cálculo
- **Email**: Envío de notificaciones
- **Slack**: Alertas en tiempo real

## Seguridad

### Para Producción:

1. Agregar autenticación a los webhooks
2. Usar API keys en headers
3. Validar IPs permitidas
4. HTTPS obligatorio
5. Rate limiting

**Ejemplo con autenticación:**

```javascript
// En n8n - Nodo HTTP Request
Headers:
  Authorization: Bearer ${API_KEY}
  Content-Type: application/json
```

## Testing

### Probar Consulta

```bash
curl http://localhost:5000/api/query/facturacion%20emitida%20de%20manera%20unitaria?limite=5
```

### Probar Webhook

```bash
curl -X POST http://localhost:5000/webhook/upload/facturacion%20emitida%20de%20manera%20unitaria \
  -H "Content-Type: application/json" \
  -d '{
    "datos": [
      {
        "fecha": "2024-01-20",
        "monto": 5000,
        "cliente": "Test Cliente"
      }
    ]
  }'
```

## Ver URLs desde el Admin Panel

1. Ir a http://localhost:5000/admin
2. Login como admin
3. Click en "Ver Datos"
4. Seleccionar un reporte
5. Click en "🔗 Webhook n8n"
6. Copiar las URLs mostradas

## Soporte

Para más información sobre n8n:

- Documentación: https://docs.n8n.io
- Comunidad: https://community.n8n.io

Para consultas sobre los endpoints del sistema, revisar:

- `backend/app.py` - Definición de rutas
- `SISTEMA_DINAMICO.md` - Arquitectura del sistema
