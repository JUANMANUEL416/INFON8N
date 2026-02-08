# 📊 Sistema Dinámico de Reportes con IA

Sistema completo de gestión y análisis de datos con inteligencia artificial, autenticación, permisos y integración con n8n.

## 🚀 Características Principales

### ✅ Gestión de Datos

- **Reportes dinámicos** configurables sin código
- **Carga masiva** de datos via Excel
- **Permisos por grupo** de usuarios
- **API REST completa** para integraciones
- **Webhooks** para n8n y otras herramientas

### 🤖 Análisis con IA

- **Chat inteligente** para hacer preguntas sobre los datos
- **Generación automática de informes** con insights
- **Búsqueda semántica** usando ChromaDB
- **Detección de tendencias y anomalías**
- **Análisis proactivo** con OpenAI GPT-4

### 🔐 Seguridad y Control

- **Autenticación** de usuarios
- **Grupos y permisos** configurables
- **Control de acceso** por reporte
- **Auditoría** de cargas y consultas

### 🔗 Integraciones

- **n8n** para automatizaciones
- **PostgreSQL** para almacenamiento
- **ChromaDB** para vectorización
- **OpenAI** para análisis IA
- **REST API** para custom integrations

---

## 🏃 Inicio Rápido

### 1. Levantar los Servicios

```bash
docker-compose up -d
```

### 2. Acceder al Sistema

- **Portal Usuario:** http://localhost:5000 (admin/admin123)
- **Panel Admin:** http://localhost:5000/admin
- **n8n:** http://localhost:5678

### 3. (Opcional) Configurar OpenAI

```bash
echo "OPENAI_API_KEY=sk-tu-api-key" > .env
docker-compose restart backend
```

---

## 💡 Funcionalidades Principales

### 1. Cargar Datos

1. Login → Seleccionar reporte
2. Descargar plantilla Excel
3. Completar y subir archivo
4. ✅ **2,883 registros cargados** (facturación)

### 2. Consultar Datos

- **Web:** Admin → Ver Datos
- **API:** `GET /api/query/{codigo}`
- **Export:** Botón "Exportar a Excel"

### 3. Chat con IA 🤖

1. Admin → Análisis IA
2. Seleccionar reporte
3. Hacer preguntas:
   - "¿Cuál es el total facturado?"
   - "¿Qué clientes tienen mayor facturación?"
   - "Muéstrame anomalías"

### 4. Generar Informes

- **Análisis General:** Vista completa
- **Tendencias:** Patrones temporales
- **Anomalías:** Detección de irregularidades
- **Informe Completo:** Todo en uno

### 5. Automatizar con n8n

- Workflows incluidos en `/n8n`
- Consultas programadas
- Alertas automáticas

---

## 📚 Documentación

- **[SISTEMA_COMPLETO.md](SISTEMA_COMPLETO.md)** - Resumen de funcionalidades
- **[ANALISIS_IA.md](ANALISIS_IA.md)** - Guía del sistema IA
- **[INTEGRACION_N8N.md](INTEGRACION_N8N.md)** - API y webhooks

---

## 🛠️ Stack Tecnológico

- Flask 3.0 + Python 3.11
- PostgreSQL 15 + JSONB
- ChromaDB 0.4.22 (vectorización)
- OpenAI GPT-4 Turbo
- n8n (automatización)
- Docker Compose

---

## 📊 Estado Actual

✅ **Sistema 100% funcional**

- 2,883 registros cargados
- Autenticación activa
- Chat IA listo (requiere API key)
- Webhooks funcionando
- n8n integrado

---

## 🆘 Soporte Rápido

```bash
# Ver logs
docker logs devprueba-backend --tail 50

# Reiniciar servicios
docker-compose restart

# Verificar estado
docker-compose ps
```

**Credenciales:** admin / admin123

---

**Sistema desarrollado con ❤️ para análisis de datos inteligente**
