# 🤖 Sistema de Análisis con IA - Guía de Uso

## Configuración Inicial

### 1. API Key de OpenAI (Opcional pero Recomendado)

Para habilitar las funcionalidades de IA, configura tu API key de OpenAI:

```bash
# Agregar al archivo .env
OPENAI_API_KEY=sk-tu-api-key-aqui
```

O configurar directamente en docker-compose.yml:

```yaml
backend:
  environment:
    - OPENAI_API_KEY=sk-tu-api-key-aqui
```

**Nota:** Sin API key, las funciones de análisis IA y chat estarán limitadas, pero la búsqueda semántica con ChromaDB seguirá funcionando.

---

## Funcionalidades Disponibles

### 1. 💬 Chat con IA

Haz preguntas en lenguaje natural sobre tus datos:

**Ejemplos de preguntas:**

- "¿Cuál es el total facturado este mes?"
- "¿Qué clientes tienen mayor facturación?"
- "Muéstrame las tendencias de los últimos 30 días"
- "¿Hay anomalías en los datos?"
- "Compara la facturación por tipo de sistema"

**Cómo usar:**

1. Ve a http://localhost:5000/admin
2. Click en "🤖 Análisis IA"
3. Selecciona un reporte
4. Ve a la pestaña "💬 Chat con IA"
5. Escribe tu pregunta y presiona Enter

**Tip:** Indexa los datos primero para respuestas más precisas (botón "🔄 Indexar Datos")

---

### 2. 📑 Generar Informes

Genera análisis automáticos con IA:

#### Análisis General

Proporciona:

- Resumen ejecutivo
- Insights principales
- Tendencias identificadas
- Recomendaciones
- Alertas o anomalías

#### Análisis de Tendencias

Identifica:

- Tendencias temporales
- Patrones recurrentes
- Proyecciones futuras
- Cambios significativos

#### Detección de Anomalías

Detecta:

- Valores atípicos
- Inconsistencias
- Datos sospechosos

#### Informe Completo

Combina todos los análisis anteriores en un documento completo.

**Cómo usar:**

1. Selecciona el reporte a analizar
2. Ve a "📑 Generar Informes"
3. Click en el tipo de análisis deseado
4. Espera (puede tomar 30-60 segundos)
5. Copia o guarda el informe generado

---

### 3. 🔍 Búsqueda Semántica

Busca información usando lenguaje natural. El sistema entiende el contexto y significado, no solo palabras clave.

**Ejemplos:**

- "Busca facturas de más de 1 millón de pesos"
- "Encuentra clientes del sector educación"
- "Muestra pagos pendientes importantes"
- "Busca transacciones anormales"

**Ventajas sobre búsqueda tradicional:**

- Entiende sinónimos y contexto
- No requiere sintaxis exacta
- Ordena por relevancia semántica
- Funciona con datos no estructurados

**Cómo usar:**

1. Ve a "🔍 Búsqueda Semántica"
2. Escribe lo que buscas en lenguaje natural
3. Selecciona cantidad de resultados
4. Click en "🔍 Buscar"

---

## Endpoints API

### Indexar Datos

```http
POST /api/analysis/{codigo}/indexar
```

Indexa los datos del reporte en ChromaDB para búsqueda semántica.

**Respuesta:**

```json
{
  "indexed": 2883,
  "collection": "reporte_facturacion_emitida_de_manera_unitaria"
}
```

---

### Hacer Pregunta (Chat)

```http
POST /api/analysis/{codigo}/pregunta
Content-Type: application/json

{
  "pregunta": "¿Cuál es el total facturado?"
}
```

**Respuesta:**

```json
{
  "pregunta": "¿Cuál es el total facturado?",
  "respuesta": "El total facturado según los datos es...",
  "contexto_usado": 5,
  "timestamp": "2026-02-08T10:00:00"
}
```

---

### Generar Análisis

```http
GET /api/analysis/{codigo}/analisis?tipo={general|tendencias|anomalias}
```

**Respuesta:**

```json
{
  "tipo_analisis": "general",
  "reporte": "Facturación Emitida",
  "total_registros": 2883,
  "analisis": "Análisis detallado generado por IA...",
  "timestamp": "2026-02-08T10:00:00"
}
```

---

### Búsqueda Semántica

```http
POST /api/analysis/{codigo}/buscar
Content-Type: application/json

{
  "consulta": "facturas importantes del mes",
  "limite": 5
}
```

**Respuesta:**

```json
{
  "pregunta": "facturas importantes del mes",
  "resultados": ["...", "..."],
  "metadatos": [{"id_registro": "123", ...}]
}
```

---

### Informe Completo

```http
GET /api/analysis/{codigo}/informe
```

Genera un informe completo con múltiples análisis.

---

## Integración con n8n

### Workflow 1: Análisis Programado

```json
Trigger: Cada día a las 8am
→ POST /api/analysis/{codigo}/analisis?tipo=general
→ Enviar informe por email
```

### Workflow 2: Chat Automatizado

```json
Webhook: Recibir pregunta
→ POST /api/analysis/{codigo}/pregunta
→ Responder vía Slack/Teams
```

### Workflow 3: Alertas de Anomalías

```json
Trigger: Cada hora
→ POST /api/analysis/{codigo}/analisis?tipo=anomalias
→ Si hay anomalías → Enviar alerta
```

---

## Casos de Uso

### 1. Dashboard Ejecutivo Diario

- Generar informe completo automáticamente
- Enviar por email a directivos
- Incluir análisis de tendencias y alertas

### 2. Asistente Virtual para Usuarios

- Los usuarios hacen preguntas sobre datos
- Sistema responde automáticamente
- Integración con Slack/Teams

### 3. Monitoreo de Anomalías

- Análisis continuo de datos nuevos
- Detección automática de irregularidades
- Alertas en tiempo real

### 4. Análisis de Negocio Ad-Hoc

- Gerentes hacen preguntas cuando lo necesiten
- Respuestas instantáneas basadas en datos
- Sin necesidad de analista

---

## Arquitectura Técnica

### Componentes

1. **ChromaDB** (Vector Database)
   - Almacena embeddings de los datos
   - Permite búsqueda semántica
   - Puerto: 8000

2. **OpenAI GPT-4**
   - Genera análisis inteligentes
   - Responde preguntas en lenguaje natural
   - Entiende contexto y produce insights

3. **PostgreSQL**
   - Almacena datos originales
   - Proporciona contexto para análisis

4. **Flask Backend**
   - Orquesta análisis
   - Gestiona APIs
   - Coordina servicios

### Flujo de Datos

```
Usuario hace pregunta
    ↓
Backend recibe pregunta
    ↓
ChromaDB busca datos relevantes (RAG)
    ↓
OpenAI analiza con contexto
    ↓
Backend formatea respuesta
    ↓
Usuario recibe análisis
```

---

## Limitaciones y Consideraciones

### Con OpenAI API Key:

- ✅ Chat completo funcional
- ✅ Generación de informes
- ✅ Análisis profundos
- ⚠️ Costo por token (~$0.01 por cada 1000 tokens)
- ⚠️ Límites de rate (depende de cuenta)

### Sin OpenAI API Key:

- ✅ Búsqueda semántica (ChromaDB)
- ✅ Indexación de datos
- ❌ Chat no disponible
- ❌ Generación de informes limitada

### Rendimiento:

- **Indexación inicial:** ~30 segundos por cada 1000 registros
- **Pregunta simple:** 2-5 segundos
- **Análisis completo:** 30-60 segundos
- **Búsqueda semántica:** <1 segundo

---

## Mejores Prácticas

1. **Indexa los datos regularmente**
   - Después de cada carga importante
   - Automatiza con n8n

2. **Preguntas específicas obtienen mejores respuestas**
   - ❌ "Analiza los datos"
   - ✅ "¿Cuál es el promedio de facturación por cliente en enero?"

3. **Usa el tipo de análisis apropiado**
   - General: Visión completa
   - Tendencias: Patrones temporales
   - Anomalías: Problemas específicos

4. **Revisa y valida**
   - La IA es muy buena, pero no infalible
   - Verifica insights importantes

5. **Controla costos**
   - Monitorea uso de OpenAI
   - Configura límites de spending
   - Usa cache cuando sea posible

---

## Troubleshooting

### "ChromaDB no disponible"

```bash
# Verificar que ChromaDB esté corriendo
docker ps | grep chroma

# Si no está corriendo
docker-compose up -d chroma
```

### "OpenAI no configurado"

- Verifica que OPENAI_API_KEY esté en .env
- Reinicia el backend después de configurar

### "Error al indexar"

- Verifica que haya datos en el reporte
- Verifica memoria disponible
- Reduce batch_size en analysis_agent.py

### Respuestas lentas

- Indexa los datos (mejora velocidad)
- Reduce número de registros consultados
- Usa análisis específicos en lugar de completo

---

## Próximas Mejoras

- [ ] Cache de respuestas frecuentes
- [ ] Fine-tuning del modelo con tus datos
- [ ] Soporte multi-idioma
- [ ] Visualizaciones automáticas
- [ ] Exportar análisis a PDF
- [ ] Histórico de conversaciones
- [ ] Sugerencias proactivas de análisis
- [ ] Integración con más LLMs (Anthropic, Llama, etc.)

---

## Soporte

- Documentación completa: `SISTEMA_COMPLETO.md`
- Integración n8n: `INTEGRACION_N8N.md`
- Guía del sistema: `SISTEMA_DINAMICO.md`
