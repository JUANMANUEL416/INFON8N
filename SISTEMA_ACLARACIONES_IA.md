# Sistema de Aclaraciones y Validaciones IA

## 📋 Descripción General

Sistema inteligente que valida automáticamente la configuración de reportes usando IA (GPT-4o), detecta campos ambiguos, solicita aclaraciones a los usuarios, permite validación por administradores y construye una base de conocimiento para mejorar futuras validaciones.

## 🎯 Flujo de Trabajo

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CREACION DE REPORTE                                          │
│    Usuario crea reporte con campos                              │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. VALIDACION AUTOMATICA IA                                     │
│    ✓ GPT-4o analiza nombres y descripciones de campos           │
│    ✓ Detecta ambigüedades y campos poco claros                  │
│    ✓ Asigna puntuación de claridad (0-100)                      │
│    ✓ Genera preguntas específicas para cada duda                │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CREACION DE ACLARACIONES                                     │
│    ✓ Por cada campo dudoso se crea registro en BD               │
│    ✓ Se almacena pregunta generada por IA                       │
│    ✓ Estado: 'pendiente'                                        │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. NOTIFICACION AL USUARIO                                      │
│    ✓ Aparece badge en menú de admin                             │
│    ✓ Usuario ve preguntas en sección "Aclaraciones"             │
│    ✓ Formulario para responder cada pregunta                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. RESPUESTA DEL USUARIO                                        │
│    ✓ Usuario explica el significado del campo                   │
│    ✓ Se guarda respuesta y marca estado 'respondida_usuario'    │
│    ✓ Se registra quién respondió y cuándo                       │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. NOTIFICACION AL ADMINISTRADOR                                │
│    ✓ Se crea notificación de tipo 'respuesta_usuario'           │
│    ✓ Aparece en panel de admin con badge contador               │
│    ✓ Admin puede ver respuesta para validar                     │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. VALIDACION POR ADMIN                                         │
│    ✓ Admin revisa respuesta del usuario                         │
│    ✓ Puede aprobarla tal cual o mejorarla                       │
│    ✓ Escribe respuesta final definitiva                         │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. BASE DE CONOCIMIENTO                                         │
│    ✓ Respuesta aprobada se guarda en tabla 'ia_aprendizaje'     │
│    ✓ Estado de aclaración: 'aprobada'                           │
│    ✓ Futuras validaciones usarán este conocimiento              │
│    ✓ IA aprende y mejora con cada aclaración                    │
└─────────────────────────────────────────────────────────────────┘
```

## 🗃️ Esquema de Base de Datos

### Tabla: `campo_aclaraciones`

Almacena aclaraciones sobre campos ambiguos de reportes.

```sql
CREATE TABLE campo_aclaraciones (
    id SERIAL PRIMARY KEY,
    reporte_codigo VARCHAR(100) NOT NULL,
    nombre_campo VARCHAR(200) NOT NULL,
    pregunta_ia TEXT NOT NULL,
    respuesta_usuario TEXT,
    respuesta_admin TEXT,
    estado VARCHAR(50) DEFAULT 'pendiente',
    aprobado BOOLEAN DEFAULT FALSE,
    fecha_pregunta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_respuesta_usuario TIMESTAMP,
    fecha_respuesta_admin TIMESTAMP,
    fecha_aprobacion TIMESTAMP,
    usuario_respondio VARCHAR(100),
    admin_respondio VARCHAR(100),
    contexto_uso TEXT,
    UNIQUE(reporte_codigo, nombre_campo)
);
```

**Estados posibles:**

- `pendiente`: Esperando respuesta del usuario
- `respondida_usuario`: Usuario respondió, esperando validación admin
- `aprobada`: Admin validó y aprobó

### Tabla: `notificaciones_admin`

Sistema de notificaciones para administradores.

```sql
CREATE TABLE notificaciones_admin (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    mensaje TEXT,
    datos JSONB,
    relacionado_con VARCHAR(50),
    relacionado_id INTEGER,
    leido BOOLEAN DEFAULT FALSE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_leido TIMESTAMP,
    admin_usuario VARCHAR(100)
);
```

**Tipos de notificación:**

- `aclaracion_requerida`: IA detectó campo ambiguo
- `respuesta_usuario`: Usuario respondió aclaración

### Tabla: `reporte_validaciones_ia`

Resultados de validaciones automáticas de IA.

```sql
CREATE TABLE reporte_validaciones_ia (
    id SERIAL PRIMARY KEY,
    reporte_codigo VARCHAR(100) NOT NULL,
    validador_ia VARCHAR(50) DEFAULT 'gpt-4o',
    resultado JSONB NOT NULL,
    campos_dudosos JSONB,
    sugerencias JSONB,
    puntuacion_claridad NUMERIC(5,2),
    aprobado_por_ia BOOLEAN DEFAULT TRUE,
    fecha_validacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validado_por VARCHAR(100)
);
```

### Tabla: `ia_aprendizaje`

Base de conocimiento para mejorar validaciones futuras.

```sql
CREATE TABLE ia_aprendizaje (
    id SERIAL PRIMARY KEY,
    tipo_aprendizaje VARCHAR(50) NOT NULL,
    contexto TEXT NOT NULL,
    pregunta_original TEXT,
    respuesta_mejorada TEXT NOT NULL,
    efectividad INTEGER DEFAULT 0,
    fuente VARCHAR(100),
    tags JSONB,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP
);
```

## 🔌 API Endpoints

### Aclaraciones

#### `GET /api/aclaraciones/<reporte_codigo>`

Obtener aclaraciones pendientes para un reporte.

**Respuesta:**

```json
{
  "success": true,
  "aclaraciones": [
    {
      "id": 1,
      "reporte_codigo": "TEST_ACLARACIONES",
      "nombre_campo": "estado",
      "pregunta_ia": "¿Qué representa específicamente el campo 'estado'?",
      "estado": "pendiente",
      "fecha_pregunta": "2026-02-08T21:59:54.123Z"
    }
  ],
  "total": 1
}
```

#### `POST /api/aclaraciones/<aclaracion_id>/responder`

Usuario responde una aclaración.

**Body:**

```json
{
  "respuesta": "El campo 'estado' representa el estado del proceso de aprobación",
  "usuario": "juan.perez"
}
```

#### `POST /api/admin/aclaraciones/<aclaracion_id>/validar`

Admin valida y aprueba respuesta.

**Body:**

```json
{
  "respuesta_final": "El campo 'estado' representa...",
  "aprobar": true,
  "admin": "admin_sistema"
}
```

#### `GET /api/admin/aclaraciones/pendientes`

Listar todas las aclaraciones pendientes de validación.

### Notificaciones

#### `GET /api/admin/notificaciones`

Obtener notificaciones no leídas.

**Query params:**

- `admin` (opcional): Filtrar por usuario admin

#### `POST /api/admin/notificaciones/<notificacion_id>/marcar-leida`

Marcar notificación como leída.

## 🎨 Interfaz de Usuario

### Panel de Admin - Sección "Aclaraciones"

**Menú lateral:**

```
📊 Gestión de Reportes
💾 Ver Datos
🤖 Análisis IA
💭 Aclaraciones  [🔴 3]  ← Badge con notificaciones
👥 Usuarios
```

**Tabs:**

1. **⏳ Pendientes de Respuesta**
   - Aclaraciones esperando respuesta del usuario
   - Muestra pregunta de la IA
   - No hay acciones disponibles

2. **✅ Requieren Validación Admin**
   - Aclaraciones respondidas por usuarios
   - Muestra pregunta de IA y respuesta de usuario
   - Botón "✅ Validar" para aprobar/mejorar

3. **📚 Base de Conocimiento**
   - Aclaraciones aprobadas históricamente
   - Muestra pregunta y respuesta final
   - Solo lectura (referencia)

**Modal de Validación:**

```
┌─────────────────────────────────────────────────┐
│ ✅ Validar Aclaración                   [X]     │
├─────────────────────────────────────────────────┤
│ 📋 Información del Campo                        │
│ Reporte: TEST_ACLARACIONES                      │
│ Campo: estado                                   │
│                                                 │
│ ❓ Pregunta de la IA:                           │
│ ┌─────────────────────────────────────────────┐ │
│ │ ¿Qué representa el campo 'estado'?          │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ 💬 Respuesta del Usuario:                       │
│ ┌─────────────────────────────────────────────┐ │
│ │ Se refiere al estado del proceso            │ │
│ │ Por: juan.perez • 08/02/2026 17:00          │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ✏️ Tu Respuesta (Admin):                        │
│ ┌─────────────────────────────────────────────┐ │
│ │ [Campo de texto editable prellenado]        │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ☑ Aprobar y agregar a base de conocimiento     │
│                                                 │
│           [Cancelar]     [✅ Validar y Guardar] │
└─────────────────────────────────────────────────┘
```

## 📊 Estadísticas

Muestra 3 cards con indicadores en tiempo real:

- **Pendientes de Usuario**: Aclaraciones sin respuesta
- **Pendientes de Validación**: Respondidas, esperando admin
- **Aprobadas Hoy**: Validaciones completadas hoy

## ⚙️ Configuración

### Variables de Entorno

```env
# Habilitar/deshabilitar validación automática
ENABLE_IA_VALIDATION=true  # Por defecto: true

# OpenAI API
OPENAI_API_KEY=sk-xxxxx...

# Base de datos
DB_HOST=postgres
DB_PORT=5432
DB_USER=admin
DB_PASSWORD=admin123
DB_NAME=informes_db
```

### Personalización

**Editar severidad de detección:**
En `backend/app.py`, línea ~140:

```python
if campo_dudoso.get('severidad') in ['alta', 'media']:
    # Crear aclaración
```

Cambiar a `['alta']` para solo campos críticos.

**Cambiar puntuación mínima:**
Modificar validación IA en `backend/analysis_agent.py`:

```python
resultado.get('puntuacion_claridad', 0) < 70  # Por defecto 60
```

## 🧪 Pruebas

### Ejecutar Suite de Pruebas

```bash
python scripts/probar_sistema_aclaraciones.py
```

**Salida esperada:**

```
🧪 PRUEBA DEL SISTEMA DE ACLARACIONES Y VALIDACIONES IA
========================================================

✅ Reporte creado exitosamente
🤖 Validación IA:
   Puntuación de claridad: 60/100
   Campos con dudas: 3
   Requiere aclaraciones: True

✅ Encontradas 3 aclaraciones
✅ Usuario respondió la aclaración correctamente
✅ Encontradas 7 notificaciones sin leer
✅ Admin validó y aprobó la aclaración

🎉 PRUEBA COMPLETADA EXITOSAMENTE
```

### Casos de Prueba Manual

1. **Crear reporte con campos ambiguos**
   - Nombre: "estado"
   - Descripción vacía
   - ✅ Debe generar aclaración

2. **Crear reporte con campos claros**
   - Nombre: "fecha_facturacion"
   - Descripción: "Fecha en que se emitió la factura al cliente en formato YYYY-MM-DD"
   - ✅ No debe generar aclaración

3. **Responder aclaración**
   - Ir a Admin → Aclaraciones
   - Tab "Requieren Validación"
   - ✅ Debe aparecer en notificaciones

4. **Validar respuesta**
   - Abrir modal de validación
   - Mejorar respuesta
   - ✅ Debe guardarse en base de conocimiento

## 📈 Métricas y Monitoreo

### Queries Útiles

**Puntuaciones promedio de claridad:**

```sql
SELECT
  AVG(puntuacion_claridad) as promedio,
  COUNT(*) as total_validaciones
FROM reporte_validaciones_ia
WHERE fecha_validacion > NOW() - INTERVAL '7 days';
```

**Top 10 campos más problemáticos:**

```sql
SELECT
  nombre_campo,
  COUNT(*) as veces_aclarado
FROM campo_aclaraciones
GROUP BY nombre_campo
ORDER BY veces_aclarado DESC
LIMIT 10;
```

**Tasa de aprobación de respuestas:**

```sql
SELECT
  COUNT(CASE WHEN aprobado THEN 1 END)::float /
  COUNT(*)::float * 100 as tasa_aprobacion
FROM campo_aclaraciones
WHERE estado = 'aprobada';
```

## 🔄 Ciclo de Mejora Continua

1. **Semana 1-2:** Sistema detecta campos ambiguos frecuentes
2. **Semana 3-4:** Usuarios responden, base de conocimiento crece
3. **Semana 5+:** IA usa conocimiento previo, reduce aclaraciones en 40-60%

## 🛠️ Mantenimiento

### Limpiar aclaraciones antiguas

```sql
DELETE FROM campo_aclaraciones
WHERE estado = 'pendiente'
AND fecha_pregunta < NOW() - INTERVAL '30 days';
```

### Exportar base de conocimiento

```sql
COPY (
  SELECT contexto, respuesta_mejorada, tags
  FROM ia_aprendizaje
  WHERE activo = TRUE
  ORDER BY efectividad DESC
) TO '/tmp/conocimiento_ia.csv' CSV HEADER;
```

## 📚 Referencias

- **Código fuente:** `backend/aclaraciones_manager.py`
- **API:** `backend/app.py` (líneas 220-333)
- **IA:** `backend/analysis_agent.py` (líneas 1018-1233)
- **UI:** `backend/templates/admin.html` (líneas 43-89, 470-555)
- **JS:** `backend/static/admin.js` (líneas 1765-2179)
- **CSS:** `backend/static/admin.css` (líneas 760-900)
- **Migración:** `backend/migrate_aclaraciones.py`

## 🎓 Capacitación

### Para Usuarios

1. Revisar notificaciones diarias en panel Admin
2. Responder aclaraciones con información clara y específica
3. Incluir ejemplos de valores válidos cuando sea posible

### Para Administradores

1. Validar respuestas dentro de 24-48 horas
2. Mejorar redacción para que sea técnica pero comprensible
3. Agregar contexto adicional si es necesario
4. Marcar como aprobado solo si la respuesta es completa

## ❓ FAQ

**P: ¿Por qué la IA no detectó campo X como ambiguo?**
R: Depende del contexto y descripción. Si tiene descripción clara, no se marca como dudoso.

**P: ¿Puedo desactivar la validación IA?**
R: Sí, configura `ENABLE_IA_VALIDATION=false` en `.env` y reinicia backend.

**P: ¿Las aclaraciones afectan reportes ya creados?**
R: No, solo sirven de referencia. El conocimiento se aplica a futuras validaciones.

**P: ¿Cuánto cuesta la validación IA con OpenAI?**
R: ~$0.001-0.003 USD por validación con GPT-4o.

## 🚀 Próximas Mejoras

- [ ] Sugerencias automáticas basadas en conocimiento previo
- [ ] Dashboard con métricas de calidad de reportes
- [ ] Exportación de aclaraciones a PDF
- [ ] Integración con Slack/Teams para notificaciones
- [ ] API para consultar conocimiento desde n8n
- [ ] Sistema de votación para respuestas (múltiples usuarios)

---

**Creado:** 2026-02-08  
**Última actualización:** 2026-02-08  
**Versión:** 1.0
